import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import asset_cache


class AssetCacheTests(unittest.TestCase):
    def test_same_resolved_image_path_is_loaded_once(self):
        image = object()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.png'
            with patch.object(asset_cache, '_load_image', return_value=image) as load:
                first = asset_cache.load_image(str(path))
                second = asset_cache.load_image(str(path.resolve()))

        self.assertIs(first, image)
        self.assertIs(second, image)
        load.assert_called_once_with(str(path.resolve()))


if __name__ == '__main__':
    unittest.main()
