import unittest

from lmk.utils import Singleton, Environment, env


class UtilsTestCase(unittest.TestCase):
    """Tests for `utils.py`."""

    def test_Singleton(self):
        """Test Singleton decorator"""

        @Singleton
        class X:
            pass

        x = X()
        y = X()
        self.assertTrue(id(x) == id(y))

    def test_Environment(self):
        """test Environment"""

        env_new = Environment()
        self.assertTrue(id(env) == id(env_new))


if __name__ == "__main__":
    unittest.main()
