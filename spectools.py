#!/usr/bin/env python

"""
Spectools provide a number of small routines to work with 1D spectra in the form
of numpy arrays or FITS files, depending on the function.

If the spectrum is specified as an array, the default is to assume that arr[:,0]
are the wavelength coordinates and arr[:,1] are the flux points.
"""

from copy import deepcopy
import pyfits as pf
from numpy import *
from scipy.integrate import trapz
from scipy.integrate import quad
from scipy.ndimage import gaussian_filter1d
from scipy import interpolate
from scipy.interpolate import interp1d
from scipy.interpolate import UnivariateSpline
from scipy.optimize import curve_fit
from scipy.optimize import fsolve
from scipy.optimize import minimize
import re

def rmbg(x,y,samp,order=1):
    """
    Removes a background function from one dimensional data.
  
    Parameters
    ----------
    x : numpy.array
    y : numpy.array
    samp : iterable
      A list of the background sampling limits
    order : integer
      Polyfit order
  
    Returns
    -------
    xnew : numpy.array
    ynew : numpy.array
    """
    xs = array([])
    ys = array([])
  
    for i in range(0,len(samp),2):
        xs = append(xs,x[(x >= samp[i]) & (x < samp[i+1])])
        ys = append(ys,y[(x >= samp[i]) & (x < samp[i+1])])
  
    p = polyfit(xs,ys,deg=order)
  
    ynew = y-polyval(p,x)
  
    return x,ynew
  
def fitgauss(x, y, p0=None, fitcenter=True, fitbg=True):
    """
    Returns a gaussian function that fits the data. This function
    requires a background subtraction, meaning that the data should
    fall to zero within the fitting limits.
            
                  (  -(mu-x)^2  )
    f(x) = m * exp| ----------- | + bg
                  (  2*sigma^2  )
    
    Parameters
    ----------
    p0 : iterable
        Initial guesses for m,mu,sigma and bg respectively
        m = maximum value
        mu = center
        sigma = FWHM/(2*sqrt(2*log(2)))
        bg = background level
    fitcenter : boolean
        Chooses whether to fit center or accept the value given
        in p0[1].
    fitbg : boolean
        Chooses wether to fit a horizontal background level or accept
        the value given in p0[3].
  
    Returns
    -------
    ans : tuple
        ans[0] = Lambda function with the fitted parameters
        ans[1] = Fit parameters
     
    """
  
    if p0 == None:
      p0 = zeros(4)
      p0[0] = y.max()
      p0[1] = where(y == y.max())[0][0]
      p0[2] = 3
      p0[3] = 1
  
    p0 = array(p0)
    p = deepcopy(p0)
    gauss = lambda t,m,mu,sigma,bg : m*exp(-(t-mu)**2/(2*sigma**2))+bg
  
    fitpars = array([True, fitcenter, True, fitbg])
  
    if not fitcenter and fitbg:
        p[fitpars] = curve_fit(lambda a, b, c, d :\
            gauss(a,b,p0[1],c,d), x,y,p0[fitpars])[0]
    elif fitcenter and not fitbg:
        p[fitpars] = curve_fit(lambda a, b, c, d :\
            gauss(a,b,c,d,p0[3]), x,y, p0[fitpars])[0]
    elif not fitcenter and not fitbg:
        p[fitpars] = curve_fit(lambda a, b, c :\
            gauss(a,b,p0[1],c,p0[3]), x,y, p0[fitpars])[0]
    else:
        p = curve_fit(gauss,x,y,p0)[0]
  
    fit = lambda t: p[0]*exp(-(t-p[1])**2/(2*p[2]**2))+p[3]
    
    p[2] = abs(p[2])
    return fit,p
  
def fwhm(x, y, bg=[0, 100, 150, 240]):
    """
    Evaluates the full width half maximum of y in units of x.
  
    Parameters
    ----------
    x : numpy.array
    y : numpy.array
    bg : list
      Background sampling limits
  
    Returns
    -------
    fwhm : number
      Full width half maximum
    """
    
  #  xnew = copy(x)
  #  ynew = copy(y)
  
  #  xc = x[(x>bg[0])&(x<bg[1]) | (x>bg[2])&(x<bg[3])]
  #  yc = y[(x>bg[0])&(x<bg[1]) | (x>bg[2])&(x<bg[3])]
  
  #  bgfit = polyfit(xc,yc,1)
  
  #  ynew = ynew-polyval(bgfit,xnew)
  
    xnew,ynew = rmbg(x, y, bg)
  
    f = UnivariateSpline(xnew, ynew/max(ynew)-.5, s=0)
    fwhm = f.roots()[1]-f.roots()[0]
  
    return fwhm

def blackbody(x,T,coordinate='wavelength'):
  """
  Evaluates the blackbody spectrum for a given temperature.

  Parameters:
  -----------
  x : numpy.array
    Wavelength or frequency coordinatei (CGS).
  T : number
    Blacbody temperature in Kelvin
  coordinate : string
    Specify the coordinates of x as 'wavelength' or 'frequency'.
  
  Returns:
  --------
  b(x,T) : numpy.array
    Flux density in cgs units.
  """

  h = 6.6261e-27  # cm**2*g/s
  c = 2.998e+10  # cm/s
  kb = 1.3806488e-16  # erg/K

  if coordinate == 'wavelength':
    b = lambda x,t : 2.*h*c**2./x**5*(1./(exp(h*c/(x*kb*t))-1.))
  elif coordinate == 'frequency':
    b = lambda x,t : 2*h*c**2/x**5*(exp((h*c)/(x*kb*t))-1)**(-1)
  
  return b(x,T)

def natural_sort(l):
  #This code is not mine! I copied it from http://stackoverflow.com/questions/4836710/does-python-have-a-built-in-function-for-string-natural-sort
  
  convert = lambda text: int(text) if text.isdigit() else text.lower() 
  alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
  return sorted(l, key = alphanum_key)
    
def closest(arr,value):

  """Returns the index of the array element that is numerically closest
  to the given value. The returned variable is an integer. This function
  expects a one-dimensional array.

  >>> closest(arange(5),3.7)
  4
  """
  
#  arr = abs(arr - value)
#  minloc = where(arr == arr.min())[0]
  
#  if minloc == array([]):
#    minloc = -1
#  else:
#    minloc = minloc[0]
    
#  return minloc

  idx = abs(arr - value).argmin()
  return idx

def get_wl(image, dimension=0, hdrext=0, dataext=0, dwlkey='CD1_1', wl0key='CRVAL1', pix0key='CRPIX1'):
  
  """
  Obtains the wavelenght coordinates from the header keywords of the
  FITS file image. The default keywords are CD1_1 for the delta lambda,
  CRVAL for the value of the first pixel and CRPIX1 for the number of
  the first pixel. These keywords are the standard for GEMINI images.
  
  The function is prepared to work with Multi-Extesion FITS (MEF) files.

  Parameters:
  -----------
  image : string
    Name of the FITS file containing the spectrum
  dimension : integer
    Dimension of the dispersion direction
  hdrext : number
    Extension that contains the header
  dataext : number
    Extension that contains the actual spectral data
  dwlkey : string
    Header keyword for the interval between two data points
  wl0key : string
    Header keyword for the first pixel value
  pix0key : string
    Header keyword for the first pixel coordinate
  
  Returns:
  --------
  wl : numpy.array
    Wavelength coordinates for each data point
  """
 
  h = pf.getheader(image,ext=hdrext)
  dwl,wl1,pix0 = [float(h[i]) for i in [dwlkey,wl0key,pix0key]]
  npoints = shape(pf.getdata(image,dataext))[dimension]
  wl = wl1 + (arange(1,npoints+1)-pix0)*dwl 
    
  return wl

def normspec(x,y,wl,span):
  
  """
  Normalizes a copy of a 1D spectrum given as arr_in, with the wavelength
  as arr_in[:,0] and the flux as arr_in[:,1]. The normalization value is the
  average flux between wl-span/2. and wl+span/2..

  Parameters:
  -----------
  x : numpy.array
    Input wavelength coordinates
  y : numpy.array
    Input flux coordinates
  wl : number
    Central wavelength for normalization
  span : number
    Width of normalization window
  """
 
#  arr = copy(column_stack([x,y]))

  y2 = copy(y)

#  if closest(x,wl-span/2.) == closest(x,wl+span/2.):
  if wl-span/2. < x[0] or wl+span/2. > x[-1]:
    print 'ERROR: Normalization wavelength outside data limits.'
    return

  f = interp1d(x,y2)
  y2 = y2/average(f(linspace(wl-span/2.,wl+span/2.,1000)))
  
  return y2

def resampspec(arr_in,dx=1,integers=True,smooth=False,swidth=1):

  """
  Resamples a 1D spectrum given as `arr_in`, with arr_in[:,0]
  being the wavelength coordinates and arr_in[:,1] being the flux.
  The resampling returns an array with one point per `dx`.
  
  Parameters
  ----------
  arr_in : two-dimensional array where arr_in[:,0] is the wavelength
           and arr_in[:,1] is the flux
  dx : the wavelenght interval of the resampled spectrum
  integers : round the wavelength coordinate to integers
  smooth : apply scipy.ndimage.gaussian_filter1d
  swidth : standard deviation for Gaussian kernel
  
  Returns
  -------
  
  arr : resampled version of arr_in
  """
  
  arr = copy(arr_in)

  f = interp1d(arr[:,0],arr[:,1])
  
  if integers:
    x0,x1 = int(arr[0,0]+1),int(arr[-1,0]-1)
  else:
    x0,x1 = arr[0,0],arr[-1,0]

  x = linspace(x0,x1,num=abs(x0-x1)/dx+1)
  
  if smooth:
    arr = column_stack([x,gaussian_filter1d(f(x),swidth)])
  else:
    arr = column_stack([x,f(x)])
 
  return arr
  
def dopcor(wl,z):
  
  """
  Applies the Doppler correction to an array of wavelength
  coordinates. z is defined as:
  
    z = (wo - we)/we 

  where `wo` is the observed wavelength and `we` is the emitted wavelength.
  
  """
  
  wlnew = copy(wl)

  wlnew = wlnew/(z+1.)
  
  return wlnew

def continuum(x,y,returns='ratio',degr=6,niterate=5,lower_threshold=2,upper_threshold=3,verbose=False):
  """
  Builds a polynomial continuum from segments of a spectrum,
  given in the form of wl and flux arrays.

  Parameters:
  -----------
  x : array-like
    Independent variable
  y : array-like
    y = f(x)
  returns : string
    Specifies what will be returned by the function
    'ratio' = ratio between fitted continuum and the spectrum
    'difference' = difference between fitted continuum and the spectrum
    'function' = continuum function evaluated at x
  degr : integer
    Degree of polynomial for the fit
  niterate : integer
    Number of rejection iterations
  lower_threshold : float
    Lower threshold for point rejection in units of standard deviation
    of the residuals
  upper_threshold : float
    Upper threshold for point rejection in units of standard deviation
    of the residuals
  verbose : boolean
    Prints information about the fitting

  Returns:
  --------
  c : tuple
    c[0] : numpy.ndarray
      Input x coordinates
    c[1] : numpy.ndarray
      See parameter "returns".    

  """
  
#  x,y = get_wl(image),pf.getdata(image)
#  if len(shape(y)) > 1:
#    if aperture == None:
#      while len(shape(y)) > 1:
#        y = y[shape(y)[1]/2]
#    else:
#      y = y[:,aperture]

  xfull = deepcopy(x)
  s = interp1d(x,y)
 
  f = lambda x : polyval(polyfit(x,s(x),deg=degr),x)
    
  for i in range(niterate):
    
    if len(x) == 0:
      print 'Stopped at iteration: {:d}.'.format(i)
      break
    sig = std(s(x)-f(x))
    res = s(x)-f(x)
    x = x[(res < upper_threshold*sig)&(res > -lower_threshold*sig)]
 
  if verbose:
    print('Final number of points used in the fit: {:d}'.format(len(x)))
    print('Rejection ratio: {:.2f}'.format(1.-float(len(x))/float(len(xfull))))

  p = polyfit(x,s(x),deg=degr)

  if returns == 'ratio':
    return xfull,s(xfull)/polyval(p,xfull)

  if returns == 'difference':
    return xfull,s(xfull)-polyval(p,xfull)

  if returns == 'function':
    return xfull,polyval(p,xfull)

def eqw(wl,flux,lims,cniterate=5):

  """
  Measure the equivalent width of a feature in `arr`, defined by `lims`:
  

  """

  fspec = interp1d(wl,flux)
  
  fctn,ctnwl = continuum(wl,flux,lims[2:],niterate=cniterate)
  
  act = trapz(polyval(fctn,linspace(lims[0],lims[1])), x=linspace(lims[0],lims[1]))  # area under continuum
  aspec = trapz(fspec(linspace(lims[0],lims[1])),linspace(lims[0],lims[1]))  # area under spectrum
  
  eqw = ((act - aspec)/act)*(lims[1]-lims[0])
   
   #Calculation of the error in the equivalent width, following the definition of Vollmann & Eversberg 2006 (doi: 10.1002/asna.200610645)
   
  sn = average(fspec(ctnwl))/std(fspec(ctnwl))
  sigma_eqw = sqrt(1+average(polyval(fctn,ctnwl))/average(flux))*(lims[1] - lims[0] - eqw)/sn
  
  return eqw,sigma_eqw

def joinspec(x1,y1,x2,y2):
  """
  Joins two spectra

  Parameters:
  -----------
  x1 : array
    Wavelength coordinates of the first spectrum
  y1 : array
    Flux coordinates of the first spectrum
  x2 : array
    Wavelength coordinates of the second spectrum
  y2 : array
    Flux coordinates of the second spectrum
  
  Returns:
  --------
  x : array
    Joined spectrum wavelength coordinates
  f : array
    Flux coordinates
  """
  
  f1 = interp1d(x1,y1,bounds_error='false',fill_value=0)
  f2 = interp1d(x2,y2,bounds_error='false',fill_value=0)

  if average(diff(x1)) <= average(diff(x2)):
    dx = average(diff(x1))
  else:
    dx = average(diff(x2))

  x = arange(x1[0],x2[-1],dx)

  f = f1(x[x < x2[0]])
  f = append(f,average(array([f1(x[(x >= x2[0])&(x < x1[-1])]),f2(x[(x >= x2[0])&(x < x1[-1])])]),axis=0))
  f = append(f,f2(x[x >= x1[-1]]))

  return x,f

def fnu2flambda(fnu,l):
  """
  Converts between flux units

  Parameters:
  -----------
  fnu : number
    Flux density in W/m^2/Hz
  l : number
    Wavelength in microns

  Returns:
  --------
  flambda: number
    Flux density in W/m^2/um

  Where does it come from?
    d nu            c
  -------- = - ---------- 
  d lambda      lambda^2
  """

  flambda = 2.99792458*fnu*10**(-12)/l**2

  return flambda

def flambda2fnu(wl,fl):
  """
  Converts a flambda to fnu.

  Parameters:
  -----------
  wl : 1d-array
    Wavelength in angstroms
  fl : 1d-array
    Flux in ergs/s/cm^2/A

  Returns:
  --------
  fnu : 1d-array
    Flux in Jy (10^23 erg/s/cm^2/Hz)
  """

  fnu = 3.33564095e+4*fl*wl**2

  return fnu

def mask(arr,maskfile):
  """
  Eliminates masked points from a spectrum.
  
  Parameters:
  -----------
  arr : ndarray
    Input spectrum for masking. The array can have
    any number of columns, provided that the wavelength
    is in the first one.
  maskfile : string
    Name of the ASCII file containing the mask definitions,
    with one region per line defined by a lower and an
    upper limit in this order.

  Returns:
  --------
  b : ndarray
    An exact copy of arr without the points that lie
    within the regions defined by maskfile.
  """
  m = loadtxt(maskfile)
  a = copy.deepcopy(arr)

  for i in range(len(m)):
    a[(a[:,0]>=m[i,0])&(a[:,0]<=m[i,1])] = 0
  
  b = a[a[:,0] != 0]

  return b

def specphotometry(spec,filt,intlims=(8,13),coords='wavelength',verbose=False,get_filter_center=False):
  """
  Evaluates the integrated flux for a given filter
  over a spectrum.

  Parameters:
  -----------
  spec : function
    A function that describes the spectrum with only
    the wavelength or frequency as parameter.
  filt : function
    The same as the above but for the filter.
  intlims: iterable
    Lower and upper limits for the integration.
  coords : string
    'wavelength' or 'frequency'
    This argument is passed directly to the function
    blackbody in the absence of a standard star spectrum.

  Returns:
  --------
  phot : float
    Photometric data point that results from the
    integration and scaling of the filter over the 
    spectrum (CGS).

  Notes:
  ------
  This method employs the scipy.integrate.quad function
  to perform all the integrations, with a limit of 1000
  and epsrel of 1.e-3.
  """

  l,er = 100,1.e-2
  x0,x1 = intlims

#  if stdstar == None:
#    stdstar = lambda x : blackbody(x*1.e-4,5.e+3,coordinate='wavelength')
  
  y2 = lambda x : filt(x)*spec(x)

  if get_filter_center:
    medianfunction = lambda x: abs(quad(filt,-inf,x,epsrel=er,limit=l)[0] - \
                                   quad(filt,x,inf,epsrel=er,limit=l)[0])
    fcenter = minimize(medianfunction,11.5,bounds=[[11.1,11.9]],method='SLSQP')
  
  cal = quad(filt,x0,x1,limit=l,epsrel=er)[0]
  phot = quad(y2,x0,x1,limit=l,epsrel=er)[0]/cal

  if verbose:
    print 'Central wavelength: {:.2f}; Flux: {:.2f}'.format(float(fcenter),phot)

  if get_filter_center:
    return phot,float(fcenter['x'])
  else:
    return phot