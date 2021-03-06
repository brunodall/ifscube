# STDLIB

# THIRD PARTY
import numpy as np
from astropy import wcs
from astropy import units
from astropy.io import fits

# LOCAL
from . import datacube, onedspec


class cube(datacube.Cube):

    def __init__(self, *args, **kwargs):

        if len(args) > 0:
            self._load(*args, **kwargs)

    def _load(self, fitsfile, redshift=0):

        self.fitsfile = fitsfile
        self.redshift = redshift

        # Opens the FITS file.
        hdu = fits.open(fitsfile)
        self.header = hdu[0].header

        self.data = hdu['F_OBS'].data
        self.header_data = hdu['F_OBS'].header
        self.fobs_norm = hdu['FOBS_NORM'].data
        self.noise_cube = hdu['F_ERR'].data
        self.flag_cube = hdu['F_FLAG'].data
        self.flags = self.flag_cube
        # self.weights = hdu['F_WEI'].data

        self.data *= self.fobs_norm
        self.noise_cube *= self.fobs_norm

        self.wcs = wcs.WCS(self.header_data)

        self.binned = False

        self._getwl()
        self._flags()
        self._spec_indices()

        # NOTE: This was probably a leftover and has been
        # commented out.
        # self.cont = hdu['F_SYN'].data * self.fobs_norm
        self.syn = hdu['F_SYN'].data * self.fobs_norm

        self.variance = np.square(self.noise_cube)
        self.stellar = self.syn

        self.weights = np.ones_like(self.data)

        hdu.close()

    def _flags(self):

        _unused = 0x0001
        no_data = 0x0002
        bad_pix = 0x0004
        ccd_gap = 0x0008
        telluric = 0x0010
        seg_has_badpixels = 0x0020
        low_sn = 0x0040

        no_obs = no_data | bad_pix | ccd_gap | _unused | telluric\
            | seg_has_badpixels | low_sn

        self.flags = self.flag_cube & no_obs

    def _spec_indices(self):

        _unused = 0x0001
        no_data = 0x0002
        bad_pix = 0x0004
        ccd_gap = 0x0008
        # telluric = 0x0010
        # seg_has_badpixels = 0x0020
        # low_sn = 0x0040

        # starlight_masked = 0x0100
        starlight_failed_run = 0x0200
        starlight_no_data = 0x0400
        # starlight_clipped = 0x0800

        # Compound flags
        no_obs = _unused | no_data | bad_pix | ccd_gap
        # before_starlight = no_obs | telluric | low_sn
        before_starlight = no_obs
        no_starlight = starlight_no_data | starlight_failed_run

        flags = before_starlight | no_starlight
        bad_lyx = (self.flag_cube & flags) > 0
        spatial_mask = (
            np.sum(bad_lyx, 0) > len(self.restwl) * 0.8
        )

        self.spatial_mask = spatial_mask

        self.spec_indices = np.column_stack([
            np.ravel(
                np.indices(np.shape(self.data)[1:])[0][~spatial_mask]),
            np.ravel(
                np.indices(np.shape(self.data)[1:])[1][~spatial_mask]),
        ])

    def _getwl(self):
        """
        Builds a wavelength vector based on the wcs object created in
        the __init__ method.

        Parameters
        ----------
        None.

        Returns
        -------
        None.
        """

        x = np.arange(self.data.shape[0])
        z = np.zeros_like(x)

        self.wl = self.wcs.wcs_pix2world(z, z, x, 0)[2]

        if self.wcs.wcs.cunit[2] == units.m:
            self.wl *= 1e+10

        if self.redshift is not None:
            self.restwl = self.wl / (1. + self.redshift)
        else:
            self.restwl = self.wl


class IntegratedSpectrum(onedspec.Spectrum):

    def __init__(self, *args, **kwargs):

        if len(args) > 0:
            self._load(*args, **kwargs)

    def _flags(self, flags):

        _unused = 0x0001
        no_data = 0x0002
        bad_pix = 0x0004
        ccd_gap = 0x0008
        telluric = 0x0010
        low_sn = 0x0040

        no_obs = no_data | bad_pix | ccd_gap | _unused | telluric | low_sn

        self.flags = flags & no_obs

    def _load(self, fname):

        self.fitsfile = fname

        with fits.open(self.fitsfile) as hdu:
            self.header = hdu['PRIMARY'].header
            t = hdu['INTEG_SPECTRA'].data

        self.data = t['f_obs']
        self.variance = np.square(t['f_err'])
        self.stellar = t['f_syn']

        self._flags(t['f_flag'])

        self.wl = t['l_obs']
        self.restwl = t['l_obs']
        self.delta_lambda = 1.0

        self.redshift = 0.0

        # A wcs will be needed to save the fits
        self._wcs_from_table()

    def _wcs_from_table(self):

        w = wcs.WCS(naxis=1)

        w.wcs.crval = np.array([self.wl[0]])
        w.wcs.crpix = np.array([0])
        w.wcs.pc = np.array([[self.delta_lambda]])
        w.wcs.ctype = ['LAMBDA']

        self.wcs = w
