# -*- coding: utf-8 -*-

# Copyright (c) 2019 Satpy developers

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""The abi_l2_nc reader tests package.
"""

import sys
import numpy as np
import xarray as xr

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

try:
    from unittest import mock
except ImportError:
    import mock


class FakeDataset(object):
    def __init__(self, info, attrs):
        for var_name, var_data in list(info.items()):
            if isinstance(var_data, np.ndarray):
                info[var_name] = xr.DataArray(var_data)

        self.info = info
        self.attrs = attrs

    def __getitem__(self, key):
        return self.info[key]

    def __contains__(self, key):
        return key in self.info

    def rename(self, *args, **kwargs):
        return self

    def close(self):
        return


class Test_NC_ABI_L2_base(unittest.TestCase):
    """Common setup for the NC_ABI_L2 reader tests."""

    @mock.patch('satpy.readers.abi_base.xr')
    def setUp(self, xr_):
        """Setup for test."""
        from satpy.readers.abi_l2_nc import NC_ABI_L2

        proj = xr.DataArray(
            [],
            attrs={
                'semi_major_axis': 1.,
                'semi_minor_axis': 1.,
                'perspective_point_height': 1.,
                'longitude_of_projection_origin': -90.,
                'sweep_angle_axis': u'x'
            }
        )
        x__ = xr.DataArray(
            [0, 1],
            attrs={'scale_factor': 2., 'add_offset': -1.},
        )
        y__ = xr.DataArray(
            [0, 1],
            attrs={'scale_factor': -2., 'add_offset': 1.},
        )

        ht_da = xr.DataArray(np.array([2, -1, -32768, 32767]).astype(np.int16).reshape((2,2)),
            dims=('y', 'x'),
            attrs={'scale_factor': 0.3052037,
                'add_offset': 0.,
                '_FillValue': np.array(-1).astype(np.int16),
                '_Unsigned': 'True',
                'units': 'm'},
        )

        xr_.open_dataset.return_value = FakeDataset({
            'goes_imager_projection': proj,
            'x': x__,
            'y': y__,
            'HT': ht_da,
            "nominal_satellite_subpoint_lat": np.array(0.0),
            "nominal_satellite_subpoint_lon": np.array(-89.5),
            "nominal_satellite_height": np.array(35786020.),
            "spatial_resolution": "10km at nadir",
            },
            {
                "time_coverage_start": "2017-09-20T17:30:40.8Z",
                "time_coverage_end": "2017-09-20T17:41:17.5Z",
            }
        )

        self.reader = NC_ABI_L2('filename',
                                {'platform_shortname': 'G16', 'observation_type': 'HT',
                                 'scan_mode': 'M3'},
                                {'filetype': 'info'})


class Test_NC_ABI_L2_get_dataset(Test_NC_ABI_L2_base):
    """Test get dataset function of the NC_ABI_L2 reader."""

    def test_get_dataset(self):
        from satpy import DatasetID
        key = DatasetID(name='HT')
        res = self.reader.get_dataset(key, {'file_key': 'HT'})

        exp_data = np.array([[2 * 0.3052037 , np.nan],
                             [32768 * 0.3052037, 32767 * 0.3052037]])

        exp_attrs = {'instrument_ID': None,
            'modifiers': (),
            'name': 'HT',
            'orbital_slot': None,
            'platform_name': 'GOES-16',
            'platform_shortname': 'G16',
            'production_site': None,
            'satellite_altitude': 35786020.,
            'satellite_latitude': 0.0,
            'satellite_longitude': -89.5,
            'scan_mode': 'M3',
            'scene_id': None,
            'sensor': 'abi',
            'timeline_ID': None,
            'units': 'm'}

        self.assertTrue(np.allclose(res.data, exp_data, equal_nan=True))
        self.assertDictEqual(dict(res.attrs), exp_attrs)


class Test_NC_ABI_L2_area_fixedgrid(Test_NC_ABI_L2_base):
    """Test the NC_ABI_L2 reader."""

    @mock.patch('satpy.readers.abi_base.geometry.AreaDefinition')
    def test_get_area_def_fixedgrid(self, adef):
        """Test the area generation."""
        self.reader.get_area_def(None)

        self.assertEqual(adef.call_count, 1)
        call_args = tuple(adef.call_args)[0]
        self.assertDictEqual(call_args[3], {'a': 1.0, 'b': 1.0, 'h': 1.0, 'lon_0': -90.0,
                                            'proj': 'geos', 'sweep': 'x', 'units': 'm'})
        self.assertEqual(call_args[4], self.reader.ncols)
        self.assertEqual(call_args[5], self.reader.nlines)
        np.testing.assert_allclose(call_args[6], (-2., -2.,  2.,  2.))


class Test_NC_ABI_L2_area_latlon(unittest.TestCase):
    """Test the NC_ABI_L2 reader."""

    @mock.patch('satpy.readers.abi_base.xr')
    def setUp(self, xr_):
        """Setup for test."""
        from satpy.readers.abi_l2_nc import NC_ABI_L2
        proj = xr.DataArray(
            [],
            attrs={'semi_major_axis': 1.,
                   'semi_minor_axis': 1.,
                   'inverse_flattening': 1.,
                   'longitude_of_prime_meridian': 0.0,
                   }
        )

        proj_ext = xr.DataArray(
            [],
            attrs={'geospatial_westbound_longitude': -85.0,
                   'geospatial_eastbound_longitude': -65.0,
                   'geospatial_northbound_latitude': 20.0,
                   'geospatial_southbound_latitude': -20.0,
                   'geospatial_lat_center': 0.0,
                   'geospatial_lon_center': -75.0,
                   })

        x__ = xr.DataArray(
            [0, 1],
            attrs={'scale_factor': 2., 'add_offset': -1.},
        )
        y__ = xr.DataArray(
            [0, 1],
            attrs={'scale_factor': -2., 'add_offset': 1.},
        )
        xr_.open_dataset.return_value = FakeDataset({
            'goes_lat_lon_projection': proj,
            'geospatial_lat_lon_extent': proj_ext,
            'lon': x__,
            'lat': y__,
            'RSR': np.ones((2, 2))}, {})

        self.reader = NC_ABI_L2('filename',
                                {'platform_shortname': 'G16', 'observation_type': 'RSR',
                                 'scene_abbr': 'C', 'scan_mode': 'M3'},
                                {'filetype': 'info'})

    @mock.patch('satpy.readers.abi_base.geometry.AreaDefinition')
    def test_get_area_def_latlon(self, adef):
        """Test the area generation."""
        self.reader.get_area_def(None)

        self.assertEqual(adef.call_count, 1)
        call_args = tuple(adef.call_args)[0]
        self.assertDictEqual(call_args[3], {'proj': 'latlong', 'a': 1.0, 'b': 1.0, 'fi': 1.0, 'pm': 0.0,
                                            'lon_0': -75.0, 'lat_0': 0.0})
        self.assertEqual(call_args[4], self.reader.ncols)
        self.assertEqual(call_args[5], self.reader.nlines)
        np.testing.assert_allclose(call_args[6], (-85.0, -20.0, -65.0, 20))


def suite():
    """The test suite for test_scene."""
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()

    mysuite.addTest(loader.loadTestsFromTestCase(Test_NC_ABI_L2_area_latlon))
    mysuite.addTest(loader.loadTestsFromTestCase(Test_NC_ABI_L2_area_fixedgrid))
    mysuite.addTest(loader.loadTestsFromTestCase(Test_NC_ABI_L2_get_dataset))

    return mysuite


if __name__ == '__main__':
    unittest.main()
