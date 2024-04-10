import datetime

import psycopg2
import psycopg2.extras

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.common_stat import StatisticsRange
from data.model.user_entity import EntityRecord

from listenbrainz.db.cover_art import get_caa_ids_for_release_mbids
from listenbrainz.webserver import db_conn

#: Minimum image size
MIN_IMAGE_SIZE = 128

#: Maximum image size
MAX_IMAGE_SIZE = 1024

#: Minimum dimension
MIN_DIMENSION = 2

#: Maximum dimension
MAX_DIMENSION = 5

#: Number of stats to fetch
NUMBER_OF_STATS = 100


class CoverArtGenerator:
    """ Main engine for generating dynamic cover art. Given a design and data (e.g. stats) generate
        cover art from cover art images or text using the SVG format. """

    CAA_MISSING_IMAGE = "https://listenbrainz.org/static/img/cover-art-placeholder.jpg"

    # This grid tile designs (layouts?) are expressed as a dict with they key as dimension.
    # The value of the dict defines one design, with each cell being able to specify one or
    # more number of cells. Each string is a list of cells that will be used to define
    # the bounding box of these cells. The cover art in question will be placed inside this
    # area.
    GRID_TILE_DESIGNS = {
        2: [
            ["0", "1", "2", "3"],
        ],
        3: [
            ["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            ["0,1,3,4", "2", "5", "6", "7", "8"],
            ["0", "1", "2", "3", "4,5,7,8", "6"],
        ],
        4: [
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
            ["5,6,9,10", "0", "1", "2", "3", "4", "7", "8", "11", "12", "13", "14", "15"],
            ["0,1,4,5", "10,11,14,15", "2", "3", "6", "7", "8", "9", "12", "13"],
            ["0,1,2,4,5,6,8,9,10", "3", "7", "11", "12", "13", "14", "15"],
        ],
        5: [[
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
            "21", "22", "23", "24"
        ], ["0,1,2,5,6,7,10,11,12", "3,4,8,9", "15,16,20,21", "13", "14", "17", "18", "19", "22", "23", "24"]]
    }

    # Take time ranges and give correct english text
    time_range_to_english = {
        "week": "last week",
        "month": "last month",
        "quarter": "last quarter",
        "half_yearly": "last 6 months",
        "year": "last year",
        "all_time": "of all time",
        "this_week": "this week",
        "this_month": "this month",
        "this_year": "this year"
    }

    def __init__(self,
                 mb_db_connection_str,
                 dimension,
                 image_size,
                 background="#FFFFFF",
                 skip_missing=True,
                 show_caa_image_for_missing_covers=True):
        self.mb_db_connection_str = mb_db_connection_str
        self.dimension = dimension
        self.image_size = image_size
        self.background = background
        self.skip_missing = skip_missing
        self.show_caa_image_for_missing_covers = show_caa_image_for_missing_covers
        self.tile_size = image_size // dimension  # This will likely need more cafeful thought due to round off errors

    def parse_color_code(self, color_code):
        """ Parse an HTML color code that starts with # and return a tuple(red, green, blue) """

        if not color_code.startswith("#"):
            return None

        try:
            r = int(color_code[1:3], 16)
        except ValueError:
            return None

        try:
            g = int(color_code[3:5], 16)
        except ValueError:
            return None

        try:
            b = int(color_code[5:7], 16)
        except ValueError:
            return None

        return r, g, b

    def validate_parameters(self):
        """ Validate the parameters for the cover art designs. """

        if self.dimension not in list(range(MIN_DIMENSION, MAX_DIMENSION + 1)):
            return "dimension must be between {MIN_DIMENSION} and {MAX_DIMENSION}, inclusive."

        bg_color = self.parse_color_code(self.background)
        if self.background not in ("transparent", "white", "black") and bg_color is None:
            return f"background must be one of transparent, white, black or a color code #rrggbb, not {self.background}"

        if self.image_size < MIN_IMAGE_SIZE or self.image_size > MAX_IMAGE_SIZE or self.image_size is None:
            return f"image size must be between {MIN_IMAGE_SIZE} and {MAX_IMAGE_SIZE}, inclusive."

        if not isinstance(self.skip_missing, bool):
            return f"option skip-missing must be of type boolean."

        if not isinstance(self.show_caa_image_for_missing_covers, bool):
            return f"option show-caa must be of type boolean."

        return None

    def get_tile_position(self, tile):
        """ Calculate the position of a given tile, return (x1, y1, x2, y2). The math
            in this setup may seem a bit wonky, but that is to ensure that we don't have
            round-off errors that will manifest as line artifacts on the resultant covers"""

        if tile < 0 or tile >= self.dimension * self.dimension:
            return (None, None)

        x = tile % self.dimension
        y = tile // self.dimension

        x1 = int(x * self.tile_size)
        y1 = int(y * self.tile_size)
        x2 = int((x + 1) * self.tile_size)
        y2 = int((y + 1) * self.tile_size)

        if x == self.dimension - 1:
            x2 = self.image_size - 1
        if y == self.dimension - 1:
            y2 = self.image_size - 1

        return (x1, y1, x2, y2)

    def calculate_bounding_box(self, address):
        """ Given a cell 'address' return its bounding box. An address is a list of comma separeated
            grid cells, which taken collectively present a bounding box for a cover art image."""

        try:
            tiles = address.split(",")
            for i in range(len(tiles)):
                tiles[i] = int(tiles[i].strip())
        except (ValueError, TypeError):
            return None, None, None, None

        for tile in tiles:
            if tile < 0 or tile >= (self.dimension * self.dimension):
                return None, None, None, None

        for i, tile in enumerate(tiles):
            x1, y1, x2, y2 = self.get_tile_position(tile)

            if i == 0:
                bb_x1 = x1
                bb_y1 = y1
                bb_x2 = x2
                bb_y2 = y2
                continue

            bb_x1 = min(bb_x1, x1)
            bb_y1 = min(bb_y1, y1)
            bb_x1 = min(bb_x1, x2)
            bb_y1 = min(bb_y1, y2)
            bb_x2 = max(bb_x2, x1)
            bb_y2 = max(bb_y2, y1)
            bb_x2 = max(bb_x2, x2)
            bb_y2 = max(bb_y2, y2)

        return bb_x1, bb_y1, bb_x2, bb_y2

    def resolve_cover_art(self, caa_id, caa_release_mbid, cover_art_size=500):
        """ Translate a release_mbid into a cover art URL. Return None if unresolvable. """
        if cover_art_size not in (250, 500):
            return None

        return f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb{cover_art_size}.jpg"

    def load_caa_ids(self, release_mbids):
        """ Load caa_ids for the given release mbids """
        with psycopg2.connect(self.mb_db_connection_str) as conn, \
                conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            return get_caa_ids_for_release_mbids(curs, release_mbids)

    def load_images(self, mbids, tile_addrs=None, layout=None, cover_art_size=500):
        """ Given a list of MBIDs and optional tile addresses, resolve all the cover art design, all the
            cover art to be used and then return the list of images and locations where they should be
            placed. Return an array of dicts containing the image coordinates and the URL of the image. """

        release_mbids = [mbid for mbid in mbids if mbid]
        results = self.load_caa_ids(release_mbids)
        covers = [
            {
                "entity_mbid": release_mbid,
                "title": results[release_mbid]["title"],
                "artist": results[release_mbid]["artist"],
                "caa_id": results[release_mbid]["caa_id"],
                "caa_release_mbid": results[release_mbid]["caa_release_mbid"]
            } for release_mbid in release_mbids
        ]
        return self.generate_from_caa_ids(covers, tile_addrs, layout, cover_art_size)

    def generate_from_caa_ids(self, covers, tile_addrs=None, layout=None, cover_art_size=500):
        """ If the caa_ids have already been resolved, use them directly to generate the grid . """
        # See if we're given a layout or a list of tile addresses
        if layout is not None:
            addrs = self.GRID_TILE_DESIGNS[self.dimension][layout]
        elif tile_addrs is None:
            addrs = self.GRID_TILE_DESIGNS[self.dimension][0]
        else:
            addrs = tile_addrs

        # Calculate the bounding boxes for each of the addresses
        tiles = []
        for addr in addrs:
            x1, y1, x2, y2 = self.calculate_bounding_box(addr)
            if x1 is None:
                raise ValueError(f"Invalid address {addr} specified.")
            tiles.append((x1, y1, x2, y2))

        # Now resolve cover art images into URLs and image dimensions
        images = []
        for x1, y1, x2, y2 in tiles:
            while True:
                cover = {}
                try:
                    cover = covers.pop(0)
                    if cover["caa_id"] is None:
                        if self.skip_missing:
                            url = None
                            continue
                        elif self.show_caa_image_for_missing_covers:
                            url = self.CAA_MISSING_IMAGE
                        else:
                            url = None
                    else:
                        url = self.resolve_cover_art(cover["caa_id"], cover["caa_release_mbid"], cover_art_size)

                    break
                except IndexError:
                    if self.show_caa_image_for_missing_covers:
                        url = self.CAA_MISSING_IMAGE
                    else:
                        url = None
                    break

            if url is not None:
                images.append({
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "url": url,
                    "entity_mbid": cover.get("entity_mbid"),
                    "title": cover.get("title"),
                    "artist": cover.get("artist"),
                })

        return images

    def download_user_stats(self, entity, user_name, time_range):
        """ Given a user name, a stats entity and a stats time_range, return the stats and total stats count from LB. """

        if time_range not in StatisticsRange.__members__:
            raise ValueError("Invalid date range given.")

        if entity not in ("artists", "releases", "recordings"):
            raise ValueError("Stats entity must be one of artist, release or recording.")

        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            raise ValueError(f"User {user_name} not found")

        stats = db_stats.get(user["id"], entity, time_range, EntityRecord)
        if stats is None:
            raise ValueError(f"Stats for user {user_name} not found/calculated")

        return stats.data.__root__[:NUMBER_OF_STATS], stats.count

    def create_grid_stats_cover(self, user_name, time_range, layout):
        """ Given a user name, stats time_range and a grid layout, return the array of
            images for the grid and the stats that were downloaded for the grid. """

        releases, _ = self.download_user_stats("releases", user_name, time_range)
        release_mbids = [r.release_mbid for r in releases]
        images = self.load_images(release_mbids, layout=layout)
        if images is None:
            return None, None

        return images, self.time_range_to_english[time_range]

    def create_artist_stats_cover(self, user_name, time_range):
        """ Given a user name and a stats time range, make an artist stats cover. Return
            the artist stats and metadata about this user/stats. The metadata dict contains
            user_name, date, time_range and num_artists. """
        
        if user_name == "huhridge":
            artists = [{"artist_mbid":"e520459c-dff4-491d-a6e4-c97be35e0044","artist_name":"Frank Ocean","listen_count":20},{"artist_mbid":"875203e1-8e58-4b86-8dcb-7190faf411c5","artist_name":"J. Cole","listen_count":13},{"artist_mbid":"e636b15f-00c5-45fd-9c33-845a08c8f92d","artist_name":"brakence","listen_count":10},{"artist_mbid":"9fff2f8a-21e6-47de-a2b8-7f449929d43f","artist_name":"Drake","listen_count":9},{"artist_mbid":"ab1a3f85-e0ea-470a-af5c-175447ae774c","artist_name":"underscores","listen_count":8},{"artist_mbid":"aea4c9b9-9f8d-49dc-b2ca-57d6f26e8634","artist_name":"Khruangbin","listen_count":8},{"artist_mbid":"3fd78e94-efeb-43a1-bc19-ad2dd1afbd5a","artist_name":"EDEN","listen_count":8},{"artist_mbid":"f6beac20-5dfe-4d1f-ae02-0b0a740aafd6","artist_name":"Tyler, the Creator","listen_count":7},{"artist_mbid":"260b6184-8828-48eb-945c-bc4cb6fc34ca","artist_name":"Charli XCX","listen_count":7},{"artist_mbid":"f1660eaa-929f-48d4-9926-9aaa61afa52f","artist_name":"Teezo Touchdown","listen_count":6},{"artist_mbid":"ab4e7869-86f5-455e-b52c-c89d7664c07b","artist_name":"Rainbow Kitten Surprise","listen_count":6},{"artist_mbid":"071409d0-ce21-4f03-a111-aec4dbc1590d","artist_name":"Erika de Casier","listen_count":6},{"artist_mbid":"381086ea-f511-4aba-bdf9-71c753dc5077","artist_name":"Kendrick Lamar","listen_count":5},{"artist_mbid":"8dc08b1f-e393-4f85-a5dd-300f7693a8b8","artist_name":"James Blake","listen_count":5},{"artist_mbid":"null","artist_name":"\u00a5$, Kanye West, Ty Dolla $ign","listen_count":4},{"artist_mbid":"164f0d73-1234-4e2c-8743-d77bf2191051","artist_name":"Ye","listen_count":4},{"artist_mbid":"61af87f4-16ee-4431-8504-cc06187079fb","artist_name":"XXXTENTACION","listen_count":4},{"artist_mbid":"926ea44c-0efa-455a-b7ce-00ccb5a86cb7","artist_name":"Kyle Dion","listen_count":4},{"artist_mbid":"00d0f0fa-a48c-416d-b4ff-25a290ce82d8","artist_name":"half\u2022alive","listen_count":3},{"artist_mbid":"8032cf05-d916-4b2a-9c53-6e75d4a24bd8","artist_name":"Trippie Redd","listen_count":3},{"artist_mbid":"87b9b3b8-ab93-426c-a200-4012d667a626","artist_name":"The War on Drugs","listen_count":3},{"artist_mbid":"aa5a6061-e60d-4a58-b9f6-c09de390bb2d","artist_name":"PnB Rock","listen_count":3},{"artist_mbid":"592da4c4-9618-4a1a-a944-e60c05c39037","artist_name":"Patrick Watson","listen_count":3},{"artist_mbid":"aa2c5e55-57f5-42a7-a0e4-4a02cd9399b1","artist_name":"Oh Wonder","listen_count":3},{"artist_mbid":"dde26295-8cd4-474c-8740-3edb801b2776","artist_name":"Maggie Rogers","listen_count":3}];

            metadata = {
                "user_name": user_name,
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "time_range": self.time_range_to_english[time_range],
                "num_artists": 128
            }
            return artists, metadata       
        artists, total_count = self.download_user_stats("artists", user_name, time_range)
        metadata = {
            "user_name": user_name,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time_range": self.time_range_to_english[time_range],
            "num_artists": total_count
        }
        return artists, metadata

    def create_release_stats_cover(self, user_name, time_range):
        """ Given a user name and a stats time range, make an release stats cover. Return
            the release stats and metadata about this user/stats. The metadata dict contains:
            user_name, date, time_range and num_releases."""

        releases, total_count = self.download_user_stats("releases", user_name, time_range)
        release_mbids = [r.release_mbid for r in releases]

        images = self.load_images(release_mbids)
        if images is None:
            return None, None, None

        metadata = {
            "user_name": user_name,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time_range": self.time_range_to_english[time_range],
            "num_releases": total_count
        }

        return images, releases, metadata
