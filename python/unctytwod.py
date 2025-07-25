#
# unctytwod.py
#

#
# Methods to transform astrometric uncertainties between frames
#

import time

import numpy as np
from covstack import CovStack

# For using numpy's polynomial convnience classes
from numpy import polynomial

# for replicating instances
import copy

# for debug plotting
from matplotlib.pylab import plt
plt.ion()

# for occasional fitting
from weightedDeltas import NormalEqs, Stack2x2

class Patternmatrix(object):

    """Sets up the pattern matrix for linear least squares fitting to
linear model

    """

    def __init__(self, deg=2, x=np.array([]), y=np.array([]), \
                 kind='Polynomial', norescale=False):

        # degree
        self.deg = deg

        # input points
        self.x = np.copy(x)
        self.y = np.copy(y)
        
        # control variable for rescaling
        self.norescale = norescale
        self.xmin = -1. # default leads to no rescaling
        self.xmax =  1.
        self.ymin = -1.
        self.ymax =  1.

        # points: x, y --> xr, yr 
        self.setlims()
        self.rescalexy()
        
        # Method selection
        self.kind=kind[:]
        self.methvander = polynomial.polynomial.polyvander2d
        self.meths = \
            { 'Polynomial':polynomial.polynomial.polyvander2d, \
              'Chebyshev':polynomial.chebyshev.chebvander2d, \
              'Legendre':polynomial.legendre.legvander2d, \
              'Hermite':polynomial.hermite.hermvander2d, \
              'HermiteE':polynomial.hermite_e.hermevander2d}

        self.setmethvander()
                
        # powers following the convention of numpy's polynomial model
        self.ipow = np.array([])
        self.jpow = np.array([])
        self.bpow = np.array([]) # boolean for powers <= deg

        # selected indices
        self.isel = np.array([])
        self.jsel = np.array([])

        # selected indices in the vandermonde array
        self.lvander = np.array([])
        
        # vandermonde array, pattern matrix
        self.vander = np.array([])
        self.pattern = np.array([])
        
        # set the indices
        self.buildpowers()
        self.selectpowers()

        # build the vandermonde array and the pattern matrix
        self.buildvander()
        self.buildpattern()

        # it's useful to be able to access the debug figure from
        # outside the instance
        self.fignum = 1

    def setlims(self):

        """Sets the domain limits for rescaling"""

        # Don't reset the limits if we're not rescaling
        if self.norescale:
            return
        
        self.xmin = np.min(self.x)
        self.xmax = np.max(self.x)

        self.ymin = np.min(self.y)
        self.ymax = np.max(self.y)
        
    def rescalexy(self):

        """Utility - rescales x, y to the [-1,1] domain"""

        self.xr = (2.0*self.x - (self.xmax + self.xmin))\
            /(self.xmax - self.xmin)
        self.yr = (2.0*self.y - (self.ymax + self.ymin))\
            /(self.ymax - self.ymin)
        
    def setmethvander(self):

        """Selects the method for the vandermonde matrix"""

        # Set a default if the selected method is not in the allowed
        # list
        if not self.kind in self.meths.keys():
            self.kind = 'Polynomial'

        self.methvander = self.meths[self.kind]
            
    def buildpowers(self):

        """Sets up the powers arrays from the degree"""

        vpow = np.arange(self.deg+1)
        self.ipow = np.repeat(vpow, self.deg+1)
        self.jpow = np.tile(vpow, self.deg+1)

    def selectpowers(self):

        """Sets boolean for powers of the proper degree"""

        self.bpow = self.ipow + self.jpow <= self.deg    

        self.isel = self.ipow[self.bpow]
        self.jsel = self.jpow[self.bpow]

        ldum = np.arange(np.size(self.ipow))
        self.lvander = ldum[self.bpow]
        
    def buildvander(self):

        """Makes vandermonde array"""

        # Note that this works on the rescaled x, y
        
        if np.size(self.xr) < 1:
            return
        
        deg2 = (self.deg, self.deg)
        self.vander = self.methvander(self.xr, self.yr, deg2)

    def initpattern(self):

        """Initialize the pattern matrix"""

        npoints = np.size(self.xr)
        ncols = 2*np.sum(self.bpow)
        nrows = 2

        self.pattern = np.zeros(( npoints, nrows, ncols))
        
    def buildpattern(self):

        """Builds the pattern matrix given the selected powers"""

        self.initpattern()
        nbases = np.size(self.lvander)

        self.pattern[:,0, 0:nbases] = self.vander[:,self.lvander]
        self.pattern[:,1, nbases::] = self.vander[:,self.lvander]
        
    def showbases(self, fignum=1, showcolorbar=False, \
                  showindices=True, fsz=6, cmap='viridis'):

        """Shows the bases"""

        # record the figure number in the instance so that we can
        # access it later
        self.fignum = fignum
        
        # index for subplots
        ldum = np.arange(np.size(self.ipow))
        lplot = ldum[self.bpow]+1

        # scale the fontsize by the degree
        fontsize=9
        if self.deg > 7:
            fontsize=6
        
        fig1=plt.figure(fignum, figsize=(fsz,fsz))
        fig1.clf()
        axes = []
        for iax in range(np.size(lplot)):
            ax = fig1.add_subplot(self.deg+1, self.deg+1, lplot[iax])

            basis = self.pattern[:, 0, iax]
            dum = ax.scatter(self.xr, self.yr, c=basis, s=2, cmap=cmap)

            # hide the vertical axis if j < 1
            if self.isel[iax] < self.deg:            
                ax.get_yaxis().set_ticklabels([])            
            if self.jsel[iax] < 1:
                ax.set_ylabel('Y', rotation=0.)
                
            if self.jsel[iax] + self.isel[iax] < self.deg:
                ax.get_xaxis().set_ticklabels([])
            else:
                ax.set_xlabel('X')
                
            # show which term this is
            if showindices:
                stitl = '%i,%i' % (self.isel[iax], self.jsel[iax])
                dum = ax.annotate(stitl, (0.05,0.95), \
                                  fontsize=fontsize, \
                                  zorder=25, \
                                  ha='left', va='top', \
                                  xycoords='axes fraction', \
                                  color='w')
    
            # add a colorbar
            if showcolorbar:
                cb = fig1.colorbar(dum, ax=ax)

        # tighten up the panels
        fig1.subplots_adjust(hspace=0.02, wspace=0.02, \
                             left=0.1, right=0.9, \
                             bottom=0.1, top=0.9)

        # supertitle
        ssup = '%s (degree %i)' % (self.kind, self.deg)
        fig1.suptitle(ssup)

class Polycoeffs(object):

    """Object and methods to translate between flat array of polynomial
coefficients and the 2D convention expected by numpy methods"""

    def __init__(self, p=np.array([]), Verbose=True, slabel='A'):

        # flat coefficients
        self.p = p

        # Print warnings?
        self.Verbose = Verbose

        # coefficients arranged as 2D array
        self.p2d = np.array([])
        
        # Degree of the corresponding polynomial (could make this -1
        # to indicate inconsistency or unfilled)
        self.deg = -1

        # arrays of x indices, y indices
        self.i = np.array([])
        self.j = np.array([])

        # Returning labels
        self.slabel=slabel[:]
        self.plotlabels = []
        
        # Populate on initialization
        self.assigndeg()
        self.assignij()

        self.initcoeffs2d()
        self.updatecoeffs2d()
        
    def degfromcoeffs(self, m=1):

        """Returns the degree given the number of coefficients"""

        d = (-3. + np.sqrt(9.0 + 8.*(m-1.) ))/2.

        return d

    def ijfromdeg(self, deg=2):

        """Returns the i, j indices for the coefficients given the degree"""

        # useful to have as a method that returns values
        
        iarr = np.array([], dtype='int')
        jarr = np.array([], dtype='int')

        for iterm in range(deg+1):
            count = np.arange(iterm+1, dtype='int')
            jarr = np.hstack(( jarr, count ))
            iarr = np.hstack(( iarr, count[::-1] ))

        return iarr, jarr

    def assigndeg(self):

        """Assigns the degree from the length of the coefficients"""

        degr = self.degfromcoeffs(np.size(self.p))

        if np.abs(degr - int(degr)) > 1.0e-3:
        #if np.abs(degr - np.int(degr)) > 1.0e-3:
            if self.Verbose:
                print("Polycoeffs.assigndeg WARN - parameters do not correspond to a degree: %i" % (np.size(self.p)))
            self.deg = -1
            return

        self.deg = int(degr)

    def assignij(self):

        """Assigns i- and j-arrays using the degree of the polynomial"""

        self.i, self.j = self.ijfromdeg(self.deg)

    def initcoeffs2d(self):

        """Sets up empty 2d array of coefficients"""

        self.p2d = np.zeros(( self.deg+1, self.deg+1 ))

    def updatecoeffs(self, p=np.array([]) ):

        """Updates the 1d and 2d coefficients from input 1d parameters"""

        # Exit gracefully if nothing passed in
        if np.size(p) < 1:
            return

        self.p = p
        self.updatecoeffs2d()
        
    def updatecoeffs2d(self):

        """Fills in the 2D coefficients array"""

        # do nothing if there is an inconsistency
        if self.deg < 1:
            if self.Verbose:
                print("Polycoeffs.updatecoeffs2d WARN - degree < 0. Check length of parameter-set")
            return
        
        l = np.arange(np.size(self.p))
        self.p2d[self.i[l],self.j[l]] = self.p[l]

    def getcoeffs2d(self, p=np.array([]), clobber=False):

        """Updates and returns the 2D coefficients for supplied parameters"""

        # If no input supplied, use whatever parameters are already
        # primed in the instance.
        if np.size(p) > 0:
            self.p = p

        # (re-) assign the degree and indices arrays if not already
        # set, OR if input keyword "clobber" is set.
        if self.deg < 0 or clobber:
            self.assigndeg()
            self.assignij()
            
        self.updatecoeffs2d()
        return self.p2d

    def setplotlabels(self, slabel='', retvals=True):

        """Utility - sets labels formatted for plotting. Not run by
default."""

        szi = np.size(self.i)
        if szi < 1:
            return

        if len(slabel) < 1:
            slabel = self.slabel[:]
            
        plotlabels = [r'$%s_{%i%i}$' % \
                      (slabel, self.i[count], self.j[count]) \
                      for count in range(szi)]

        # either return OR update the instance, but not both.
        if retvals:
            return plotlabels

        self.plotlabels = plotlabels[:]
        self.slabel = slabel[:]

class Parvec(object):

    """Polynomial parameters and tangent point parameters"""

    # Mainly so that I don't have to type the same thing a few times
    
    def __init__(self, pars=np.array([]) ):

        # Do the parameters contain separate x0, y0 parameters?
        self.hasxy0 = True

        # utility attribute - which parameters correspond to
        # (a,b,c,d,e,f) in 6-term transformation
        self.inds1d_6term = np.array([])
        
        # Ingest the parameters on initialization
        self.initpars()
        self.ingestpars(pars)
        
    def initpars(self):

        """Initializes the parameters"""

        self.parsx = np.array([])
        self.parsy = np.array([])
        self.tangentpoint = np.array([])

    def ingestpars(self, pars=np.array([]) ):

        """Splits the input parameters array into pointing (first two
parameters) and parsx, parsy for the polynomial (everything else).

Inputs:

        pars = [alpha0, delta0, parsxy] - 1D array of full parameters

Returns: N/A
        
        Updates instance attributes.

"""

        if np.size(pars) < 2:
            return

        self.tangentpoint = pars[0:2]

        # Handle the remaining parameters
        if np.size(pars) < 3:
            return

        parsxy = pars[2::]
        nxy = np.size(parsxy)
        imid = int(nxy*0.5)
        
        # Need to be able to actually split this for the parameters to
        # be valid
        if nxy % 2 > 0:
            return
        
        imid = int(nxy*0.5)
        parsx = parsxy[0:imid]
        parsy = parsxy[imid::]

        # Set the attribute for the abcdef parameters
        self.inds1d_6term = [0,2,3,1, imid+2, imid+3]
        
        PC = Polycoeffs(Verbose=False)
        degx = PC.degfromcoeffs(parsx.size)
        if degx - int(degx) > 0:
            degx = PC.degfromcoeffs(parsx.size+1)

            # If this *still* isn't an integer, the polynomial class
            # isn't going to handle the parameters. In that instance,
            # return without populating them.
            if degx - int(degx) > 0:
                if self.Verbose:
                    print("Parvec.ingestpars WARN - parsx does not correspond to a polynomial degree. Returning.")
                return

            # If the parameters *do* correspond to polynomial with no
            # x0, y0 component, set the appropriate indicator and
            # produce the parameters in the form Poly() will expect.
            self.hasxy0 = False
            self.parsx = np.hstack(( 0., parsx ))
            self.parsy = np.hstack(( 0., parsy ))
            return
            
        self.parsx = np.copy(parsx)
        self.parsy = np.copy(parsy)

        
        
class Poly(object):

    """Methods to transform positions and uncertainties using numpy's
polynomial objects and methods. Should allow polynomials, legendre,
chebyshev and hermite depending on which of numpy's methods we
choose.

Inputs:

    x = [N] array of x positions

    y = [N] array of y positions

    covxy = [N,2,2] array of x,y covariances

    parsx = [M] array of x polynomial parameters (interpreted as 2M
    polynomial parameters for x and y if checkparsy is True)

    parsy = [M] array of y polynomial parameters (ignored if
    checkparsy is True)

    degrees = all angles measured in degrees

    kindpoly = which kind of polynomial? (Chebyshev, Polynomial, Legendre,
    etc.)

    Verbose = print to screen
    
    xmin, xmax, ymin, ymax = data limits. Used to rescale (x,y) to
    (-1, 1), and NOT necessarily the minmax of the data itself. 

    xisxi = adjust plot labels so that we're going from (xi, eta) to
    (x,y). If False, the input x, y are assumed to be detector X, Y.

    checkparsy = split parsx across parsx and parsy

    radec = unused, included for compatibility

    covradec = unused, included for compatibility

    """

    # WATCHOUT - numpy's convenience methods DO account for the domain,
    # but the convenience *functions* like chebval2d DO NOT. However,
    # in the numpy implementation, series cannot be multiplied if
    # their domains are different, which will be problematic when
    # trying to evaluate 2D polynomials. So, we rescale within the
    # instance and force the [-1., 1.] domain. This wll require some
    # other methods to handle the scaling when evaluating the
    # polynomials and their derivatives. That's annoying.

    # Notice that the xmin, xmax, ymin, ymax are the bounds of the
    # detector, and NOT the limits of x and y themselves. If xmin
    # etc. are not set then errors can result.

    # If parsx is supplied but NOT parsy, this class assumes both are
    # contained in parsx, and splits it across both.
    
    def __init__(self, x=np.array([]), y=np.array([]), covxy=np.array([]), \
                 parsx=np.array([]), parsy=np.array([]), degrees=True, \
                 kindpoly='Polynomial', Verbose=False, \
                 xmin=None, xmax=None, ymin=None, ymax=None, \
                 xisxi=False, checkparsy=False, \
                 radec=None, covradec=None):

        # Inputs
        #self.x = x
        #self.y = y
        #self.covxy = covxy

        # Use the same method we'll use later on if we update
        self.x = np.array([])
        self.y = np.array([])
        self.covxy = np.array([])
        self.updatedata(x, y, covxy)
        self.parsx = np.array(parsx)
        self.parsy = np.array(parsy)

        # If parsx supplied but not parsy, splits parsx across both,
        # but ONLY if this behavior is selected.
        if checkparsy:
            self.checkparsxy()
        
        # Domains for the polynomials
        self.updatelimits(xmin, xmax, ymin, ymax)
        #self.xmin = xmin
        #self.xmax = xmax
        #self.ymin = ymin
        #self.ymax = ymax

        # control variable (for scaling deltas)
        self.degrees = degrees
        
        # control variable
        self.Verbose = Verbose

        # Convenience labels for plots
        self.labelx=r'$\xi$'
        self.labely=r'$\eta$'
        self.labelxtran = 'X'
        self.labelytran = 'Y'

        # Flip the meaning of the labels if we're going from x,y to
        # (xi, eta)
        if not xisxi:
            self.labelxtran = self.labelx[:]
            self.labelytran = self.labely[:]
            self.labelx = 'X'
            self.labely = 'Y'

        # Derivatives that will be evaluated at x, y to evaluate the
        # jacobian for given input positions
        self.cxx = np.array([])
        self.cxy = np.array([])
        self.cyx = np.array([])
        self.cyy = np.array([])
            
        # rescaled x, y to the [-1, 1] interval, and scaling factors
        self.jacrescale = np.eye(2)
        self.setdomain()
        self.setjacrescale()
        #self.rescalepos()  # in updatejacobian()

        # No matter which choice of polynomial, the first three
        # coefficients in each direction are {a,b,c} in {a + bx +
        # cy}. Note that these are the indices in the abutted {parsx,
        # parsy, nuisance} parameters vector that will be output from
        # the MCMC.
        self.inds1d_6term = np.array([])
        self.setinds_6term()
        
        # Coefficients objects (to handle the translation from 1D
        # input to the 2D that the polynomial methods will expect:
        self.setuppars()

        # 2024-11-12 note: updated these names to _list just now to
        # avoid overloading.
        self.methval2dlist = {'Polynomial':polynomial.polynomial.polyval2d, \
                          'Chebyshev':polynomial.chebyshev.chebval2d, \
                          'Legendre':polynomial.legendre.legval2d, \
                          'Hermite':polynomial.hermite.hermval2d, \
                          'HermiteE':polynomial.hermite_e.hermeval2d}

        self.methderlist = {'Polynomial':polynomial.polynomial.polyder, \
                        'Chebyshev':polynomial.chebyshev.chebder, \
                        'Legendre':polynomial.legendre.legder, \
                        'Hermite':polynomial.hermite.hermder, \
                        'HermiteE':polynomial.hermite_e.hermeder}

        
        # Polynomial object and methods to use
        self.polysallowed = list(self.methderlist.keys()) # 2024-07-27 made a list
        self.kind = kindpoly[:]
        self.checkpolysupported()
        self.setmethods()
        
        # self.setpoly() # NO LONGER USING CONVENIENCE CLASSES

        # Now instantiate the convenience classes for this choice of
        # polynomial
        # self.makepolys()
        
        # The jacobian for the transformation, transformed coords,
        # transformed covariances
        self.jacpoly = np.array([]) # jacobian for the polynomial only
        self.jac = np.array([]) # jacobian including rescaling

        # We set up the jacobian given input parameters now
        # self.getjacobian() # in updatejacobian()
        
        self.xtran = np.array([])
        self.ytran = np.array([])
        self.covtran = np.array([])

        # convenience variable - xytran as [N,2]
        self.xytran = np.array([])
        ## self.initxytran() # moved to updatejacobian

        # Initialize attributes that depend on the input data,
        # particularly the jacobians.
        self.updatejacobian()
        

    def checkparsxy(self):

        """If the parsx array was populated but not the parsy array, this
method tries to split the parsx across the parsx and parsy
arrays. This is mainly aimed as a labor-saving device for the calling
array.

        """

        # Cannot partition parsx in two if it is of zero or odd size
        if np.size(self.parsx) < 0:
            return

        if np.size(self.parsx) % 2 > 0:
            return

        npx = int(np.size(self.parsx)/2)
        self.parsy = self.parsx[npx::]
        self.parsx = self.parsx[0:npx]

    def setinds_6term(self):

        """Utility - sets identifier attribute for the indices in the final 1d
parameter set {parsx, parsy, any nuisance parameters...} that
corresponds to {a,b,c,d,e,f} in 

        xi = a + bx + cy
        eta = d + ex + fy

        """

        l3 = np.arange(3, dtype='int')
        self.inds1d_6term = np.hstack(( l3, l3 + np.size(self.parsx) ))
        
    def initxytran(self):

        """Utility - initializes xytran convenience variable using the size of
the dataset"""

        npts = np.size(self.x)
        self.xytran = np.zeros(( npts, 2 ))
        
    def setdomain(self, clobber=False):

        """Sets the domain (for rescaling to [-1., 1.] If clobber is set, then any user-input limits not outside the domain of the data are overridden."""

        # Allow passing in to the instance as user-supplied
        # variables.

        # Note that the user doesn't need to supply actual data, only
        # the minmax values. If all four are supplied, this is valid.

        nx = np.size(self.x)
        ny = np.size(self.y)

        # self.xmin is an np.ndarray even if None is passed in...
        # so self.xmin is None --> self.xmin == None throughout this method
        
        if self.xmin == None:
            if nx > 0:
                self.xmin = np.min(self.x)
            else:
                self.xmin = -1.
        else:
            if nx > 0 and clobber:
                self.xmin = np.min([self.xmin, np.min(self.x)])
            
        if self.xmax == None:
            if nx > 0:
                self.xmax = np.max(self.x)
            else:
                self.xmax = 1.
        else:
            if nx > 0 and clobber:
                self.xmax = np.max([self.xmin, np.max(self.x)])

        if self.ymin == None:
            if ny > 0:
                self.ymin = np.min(self.y)
            else:
                self.ymin = -1.
        else:
            if ny > 0 and clobber:
                self.ymin = np.min([self.ymin, np.min(self.y)])
            
        if self.ymax == None:
            if ny > 0:
                self.ymax = np.max(self.y)
            else:
                self.ymax = 1.
        else:
            if ny > 0 and clobber:
                self.ymax = np.max([self.ymin, np.max(self.y)])

    def setjacrescale(self):

        """Sets the jacobian for the rescaling of the input positions"""
                
        self.jacrescale = np.array( [[2.0/(self.xmax - self.xmin), 0.], \
                                     [0., 2.0/(self.ymax - self.ymin)] ] )

        
    def rescalepos(self):

        """Rescales x, y to the interval [-1., 1.], computing the jacobian for
this rescaling"""
        
        self.xr, self.yr = self.rescalexy(self.x, self.y)

    def rescalexy(self, x=np.array([]), y=np.array([])):

        """Rescales input x, y using the limits set for the object"""

        xr = (2.0*x - (self.xmax + self.xmin))/(self.xmax - self.xmin)
        yr = (2.0*y - (self.ymax + self.ymin))/(self.ymax - self.ymin)

        return xr, yr
        
    def setuppars(self):

        """Updates the parameters-objects given the instance parameters"""
        
        self.pars2x = Polycoeffs(self.parsx, Verbose=self.Verbose)
        self.pars2y = Polycoeffs(self.parsy, Verbose=self.Verbose)
        
    def checkpolysupported(self):

        """Checks whether the requested polynomial type is supported
        """

        # Implemented using a list of known-allowed rather than just
        # using try/except because the exception handler could be
        # slow.
        
        if not self.kind in self.polysallowed:
            if self.Verbose:
                print("Poly.checkpoly WARN - supplied polynomial %s not found. Defaulting to Polynomial" % (self.kind))

            self.kind='Polynomial'

    def setmethods(self):

        """Selects the methods by which polynomials will be manipulated"""

        # Because the convenience classes do not have the *val2d
        # methods, we drop back to the functions provided by
        # numpy. This means more footwork in identifying the methods
        # to use.

        # We actually could construct this using comprehension of the
        # labels since numpy's convention is adhered to so
        # well. However it's probably easiest to debug if the methods
        # are just stated explicitly. All the ones below use unlimited
        # domain or [-1., 1.] domain. (Laguerre uses [0,1]). For all
        # but the Hermite, the n=1 entry is just "x", which will make
        # testing the linear case easier.
        
        self.methval2d = self.methval2dlist[self.kind]
        self.methder = self.methderlist[self.kind]
        
    def setpoly(self):

        """Sets up the kind of polynomial object we want"""
            
        self.P = getattr(polynomial, self.kind)

    def setdomains(self):

        """Sets the data domains for the input data"""

        # 2024-11-07 these attributes are now never used. Call removed.
        
        self.domainx = np.array([np.min(self.x), np.max(self.x) ])
        self.domainy = np.array([np.min(self.y), np.max(self.y) ])
        
    def makepolys(self):

        """Creates the polynomial convenience objects"""

        self.polx = self.P(self.parsx)
        self.poly = self.P(self.parsy)

    def propxy(self, x=np.array([]), y=np.array([]) ):

        """Propagates input x, y positions to target frame, returning transformed positions as arrays"""

        if np.size(x) < 1 or np.size(y) < 1:
            return np.array([]), np.array([])

        xr, yr = self.rescalexy(x, y)
        xtran = self.methval2d(xr, yr, self.pars2x.p2d)
        ytran = self.methval2d(xr, yr, self.pars2y.p2d)

        return xtran, ytran
        
    def tranpos(self):

        """Applies the transformation to the raw positions, updating instance quantities self.xtran, self.ytran"""

        self.xtran, self.ytran = self.propxy(self.x, self.y)
        
    def tranpos_r(self):

        """Applies the transformation (to the RESCALED positions over the
domain [-1, 1])"""

        self.xtran = self.methval2d(self.xr, self.yr, self.pars2x.p2d)
        self.ytran = self.methval2d(self.xr, self.yr, self.pars2y.p2d)

    def derivcoeffs(self, c=np.array([]) ):

        """Given a 2d set of coefficients for a polynomial, returns the
derivative wrt x as a coefficient set with the same dimensions as the
original (i.e. padded at the highest power).

        """

        # if c is blank
        if len(np.shape(c)) < 1:
            return np.array([])

        # if fed scalar or 1d coefficients
        if np.ndim(c) < 2:
            return np.array([0])

        # Find the derivative along each axis...
        cdx = self.methder(c, 1,1,axis=0)
        cdy = self.methder(c, 1,1,axis=1)

        # ... and pad so that the outputs are square with same dimensions
        # as inputs.
        cdx = np.pad(cdx, [[0,1], [0,0]] )
        cdy = np.pad(cdy, [[0,0], [0,1]] )

        return cdx, cdy

    def setderivcoeffs(self):

        """Sets up the coefficients of the polynomial derivatives that will be
evaluated at x,y to populate the jacobian"""

        self.cxx, self.cxy = self.derivcoeffs(self.pars2x.p2d)
        self.cyx, self.cyy = self.derivcoeffs(self.pars2y.p2d)
        
    def initjacpoly(self):

        """Initializes the jacobian for the polynomial using the
characteristics of the data, to the identity, [N,2,2] """

        nobjs = np.size(self.x)
        if nobjs < 1:
            self.jacpoly = np.array([])
            return
        
        self.jacpoly = np.zeros(( nobjs, 2, 2 ))
        self.jacpoly[:,0,0] = 1.
        self.jacpoly[:,1,1] = 1.
        
    def populatejacpoly(self):

        """Computes the jacobian for the transformation represented by the
polynomial"""

        # We assume the jacobian has already been initialized. If not,
        # return.
        if np.size(self.jacpoly) < 2:
            if self.Verbose:
                print("Poly.populatejacpoly WARN - jacobian < 2 elements. Not initialized yet?")
            return

        # Compute the coefficients... 
        self.setderivcoeffs()

        # ... and evaluate them at the datapoints
        self.jacpoly = self.evaluatejacpoly(self.xr, self.yr)

        # this is if we already have an instance-level we want to fill in
        #self.jacpoly[:,0,0] = self.methval2d(self.xr, self.yr, self.cxx)
        #self.jacpoly[:,0,1] = self.methval2d(self.xr, self.yr, self.cxy)
        #self.jacpoly[:,1,0] = self.methval2d(self.xr, self.yr, self.cyx)
        #self.jacpoly[:,1,1] = self.methval2d(self.xr, self.yr, self.cyy)

    def evaluatejacpoly(self, xr=np.array([]), yr=np.array([]) ):

        """Evaluates the jacobian corresponding to the [-1,1] x, y"""

        if np.size(xr) < 1 or np.size(yr) < 1:
            return np.array([])

        jacpoly = np.zeros(( xr.size, 2, 2 ))
        jacpoly[:,0,0] = self.methval2d(xr, yr, self.cxx)
        jacpoly[:,0,1] = self.methval2d(xr, yr, self.cxy)
        jacpoly[:,1,0] = self.methval2d(xr, yr, self.cyx)
        jacpoly[:,1,1] = self.methval2d(xr, yr, self.cyy)

        return jacpoly
        
    def combinejac(self):

        """Utility - combines the jacobians for rescaling and polynomial into
a single jacobian"""

        # 2024-09-04 return gracefully if either array is empty
        if np.size(self.jacrescale) < 1:
            return
        
        if np.size(self.jacpoly) < 1:
            return
        
        # numpy's matmul handles broadcasting for us. 
        self.jac = np.matmul( self.jacrescale, self.jacpoly )

    def getjacobian(self):

        """One-liner to get the jacobians for the rescaling and polynomial"""

        self.setjacrescale()
        if np.size(self.jacpoly) < 2:
            self.initjacpoly()
            
        self.populatejacpoly()
        self.combinejac()

    def updatedata(self, x=np.array([]), y=np.array([]), \
                   covxy=np.array([]), \
                   xy=np.array([]) ):

        """Ingests supplied data to populate x, y, covars. 

Inputs:


        x = [N] array of X-values. 

        y = [N] array of Y-values

        covxy = [N,2,2] array of XY covariances

        xy = [N,2] xy array. If set, supersedes x, y.

Outputs:
        None - internal attributes self.x, self.y, self.covxy

"""

        # Positions
        if np.ndim(xy) == 2:
            self.x = xy[:,0]
            self.y = xy[:,1]
        else:
            self.x = np.copy(x)
            self.y = np.copy(y)
            
        # covariances. We parse here for matching size with the
        # positions before updating
        if np.ndim(covxy) != 3:
            return

        ndata = np.size(self.x)
        ncov = np.shape(covxy)[0]

        if ndata != ncov:
            return

        self.covxy = np.copy(covxy)

    def updatejacobian(self):

        """One-liner to prepare for transformation using updated data"""

        # DO NOT update the domain here. If we want to apply the same
        # transformation on new data, we need the domain of the old
        # transformation to get it right. For that reason, we do NOT
        # call setjacrescale() here.
        
        self.rescalepos()
        self.getjacobian()
        self.initxytran()
        
    def ingestdata(self, x=np.array([]), y=np.array([]), covxy=np.array([]), \
               xy=np.array([]) ):

        """Ingests supplied data to populate x, y, covars, and updates the rescaling and the jacobians accordingly.

Inputs:


        x = [N] array of X-values. 

        y = [N] array of Y-values

        covxy = [N,2,2] array of XY covariances

        xy = [N,2] xy array. If set, supersedes x, y.

        """

        # First, update the data
        self.updatedata(x, y, covxy, xy)

        # then the jacobians and other attributes that need to change
        self.updatejacobian()
        
    def trancov(self):

        """Transforms the covariances from the unrescaled originals to the
target frame. Updates self.covtran in the instance."""

        if np.size(self.jac) < 2:
            self.getjacobian()

        if np.size(self.covxy) < 2:
            if self.Verbose:
                print("Poly.trancov WARN - self.covxy size < 2")
                return
            return

        self.covtran = self.propcov(self.covxy, self.x, self.y)
        
    def propcov(self, C=np.array([]), x=np.array([]), y=np.array([]) ):

        """Propagates unrescaled covariances from input to output frame, returning the transformed covariances as an [N,2,2] array."""

        # First compute the jacobian
        xr, yr = self.rescalexy(x,y)
        Jpoly = self.evaluatejacpoly(xr, yr)
        J = np.matmul( self.jacrescale, Jpoly )
        
        # J = self.jac
        Jt = np.transpose(J,axes=(0,2,1))

        return np.matmul(J, np.matmul(C, Jt) )
        

    def nudgepos(self, dxarcsec=10., dyarcsec=10.):

        """Nudges the input positions. Beware - this will happily send positions outside the domain of the polynomial."""

        # conv = 206265.
        conv = 1.  # if units are radians or pixels
        if self.degrees:
            conv = 3600.

        self.x += dxarcsec / conv
        self.y += dyarcsec / conv
            
    def calcdeltas(self, dxarcsec=10., dyarcsec=10.):

        """Utility - given the jacobian for the transformation, compute the
deltas from J.dx"""

        if np.size(self.jac) < 1:
            return np.array([])

        # delta-array will be in the same units as the original
        # coordinates, assuming the input deltas are in arcsec
        #conv = 206265.
        conv = 1. # if units are radians or pixels
        if self.degrees:
            conv = 3600.

        dx = np.array([dxarcsec, dyarcsec])/conv
        dv = np.matmul(self.jac, dx)

        return dv
            
    def propagate(self):

        """Propagates the positions and covariances from raw to target
frame"""

        # We assume the jacobian has already been populated.

        self.tranpos()
        self.trancov()

        self.xytran[:,0] = self.xtran
        self.xytran[:,1] = self.ytran
        
    def splitpars(self, pars=np.array([]) ):

        """Utility: splits 1D params into two half-length lists"""

        npars = np.size(pars)
        if npars < 2:
            return np.array([]), np.array([])

        imid = int(npars/2)
        return pars[0:imid], pars[imid::]

    def updatelimits(self, xmin=None, xmax=None, ymin=None, ymax=None):

        """Updates the limits.

        WATCHOUT - calling this with no arguments will cause the
        instance limits to revert to [None, None, None, None].

        """

        self.xmin = np.copy(xmin)
        self.xmax = np.copy(xmax)
        self.ymin = np.copy(ymin)
        self.ymax = np.copy(ymax)
        
    def updatetransf(self, pars=np.array([]) ):

        """Updates the transformation and relevant quantities from input
parameters. Anticipating the eventual use-case, the x and y parameters are assumed to be abutted together"""

        parsx, parsy = self.splitpars(pars)

        if np.size(parsx) < 1:
            return

        # the 1d parameters are not used. Set for consistency
        self.parsx = np.copy(parsx)
        self.parsy = np.copy(parsy)

        # If this instance was originally blank, self.pars2x and
        # self.pars2y might not be set up yet. If so:
        if self.pars2x.deg < 0:
            self.setuppars()
        
        # ... the 2d parameters...
        self.pars2x.updatecoeffs(parsx)
        self.pars2y.updatecoeffs(parsy)

        # ... the derivative coefficients...
        self.setderivcoeffs()
        
        # ... and the jacobian
        self.populatejacpoly()
        self.combinejac()

    def getlabels(self, labelx='A', labely='B', retboth=False):

        """Returns parameter labels. 

Inputs:

        labelx = string for the front of x-labels

        labely = string for the front of y-labels

        retboth = return separate arguments rather than appended together

"""

        labelsx = self.pars2x.setplotlabels(labelx)
        labelsy = self.pars2x.setplotlabels(labely)

        if retboth:
            return labelsx, labelsy
        
        return labelsx + labelsy
        
class Polynom(object):

    """Methods to transform positions and uncertainties via
polynomial. Note this is not invertible, so we only provide methods in
the one direction."""

    def __init__(self, posxy=np.array([]), covxy=np.array([]), \
                 parsx=np.array([]), parsy=np.array([]), \
                 degrees=True):

        self.x = posxy[:,0]
        self.y = posxy[:,1]

        self.covxy = covxy

        # transformation parameters for x, y coords
        self.parsx = parsx
        self.parsy = parsy

        # Jacobian for the transformation
        self.jac = np.array([])

        # Transformed coordinates, covariances
        self.xtran = np.array([])
        self.ytran = np.array([])
        self.covtran = np.array([])

        # calling routines may want transformed coords in [N,2] format
        self.xytran = np.zeros(( np.size(self.x), 2))
        
        # control variable - original coords are in degrees?
        self.degrees = degrees

        # Labels for the transformed quantities
        self.labelxtran = r'$X$'
        self.labelytran = r'$Y$'

    def polyval2d(self, pars=np.array([])):

        """Evaluates the polynomial for the instance-level coordinates"""

        # This is written out by hand for readability and for ease
        # translating to the jacobians later on. Might be better to
        # use rules to construct all the powers, but that requires
        # cleverer list comprehension chops than I currently have.
        
        # This really serves to establish our convention for the
        # coefficients throughout this object.
        z = self.x * 0. + pars[0] # inherit the shape of x
        if np.size(pars) < 2: # want this to work on scalar pars
            return z

        # add linear terms...
        z += self.x * pars[1] + self.y * pars[2]
        if np.size(pars) < 6:
            return z

        # second-order...
        z += self.x**2 * pars[3] + self.x*self.y*pars[4] + self.y**2 * pars[5]
        if np.size(pars) < 10:
            return z

        # third order...
        z += self.x**3 * pars[6] + \
            self.x**2 * self.y    * pars[7] + \
            self.x    * self.y**2 * pars[8] + \
            self.y**3 * pars[9]
        if np.size(pars) < 15:
            return z
        
        # fourth order...
        z += self.x**4            * pars[10] + \
            self.x**3 * self.y    * pars[11] + \
            self.x**2 * self.y**2 * pars[12] + \
            self.x    * self.y**3 * pars[13] + \
                        self.y**4 * pars[14]
        if np.size(pars) < 21:
            return z
        
        # fifth-order
        z += self.x**5 * pars[15] + \
            self.x**4 * self.y    * pars[16] + \
            self.x**3 * self.y**2 * pars[17] + \
            self.x**2 * self.y**3 * pars[18] + \
            self.x * self.y**4 * pars[19] + \
            self.y**5 * pars[20]

        return z
        
        # ... beyond fifth order, consider iterations (would need
        # something clever for the covariances)

    def jac2d(self, pars=np.array([]) ):

        """Returns the Jacobian terms dz/dx, dz/dy when z=polyval2d(pars,
x,y)). Coordinates are taken from the instance, pars are passed in as
arguments
        """

        #dz/dx, dz/dy
        zx = self.x * 0.
        zy = self.y * 0.

        if np.size(pars) < 2:
            return zx, zy

        # first order
        zx += self.x * 0. + pars[1]
        zy += self.y * 0. + pars[2]
        if np.size(pars) < 6:
            return zx, zy

        # second order - now the coordinates finally get involved
        zx += 2.0*self.x * pars[3] + self.y*pars[4]
        zy += 2.0*self.y * pars[5] + self.x*pars[4]
        if np.size(pars) < 10:
            return zx, zy

        # third order
        zx += \
            3.0*self.x**2 * pars[6] + \
            2.0*self.x*self.y*pars[7] + \
            self.y**2 * pars[8]

        zy += \
            self.x**2 * pars[7] + \
            2.0*self.y * self.x * pars[8] + \
            3.0*self.y**2 * pars[9]
        if np.size(pars) < 15:
            return zx, zy

        # fourth order
        zx += \
            4.0*self.x**3 * pars[10] + \
            3.0*self.x**2 * self.y * pars[11] + \
            2.0*self.x * self.y**2 * pars[12] + \
            self.y**3 * pars[13]

        zy += \
            self.x**3 * pars[11] + \
            2.0 * self.y * self.x**2 * pars[12] + \
            3.0 * self.y**2 * self.x * pars[13] + \
            4.0 * self.y**3 * pars[14]
        if np.size(pars) < 21:
            return zx, zy

        # fifth-order
        zx += \
            5.0*self.x**4 * pars[15] + \
            4.0*self.x**3 * self.y * pars[16] + \
            3.0*self.x**2 * self.y**2 * pars[17] + \
            2.0*self.x    * self.y**3 * pars[18] +\
            self.y**4 * pars[19]

        zy += \
            self.x**4 * pars[16] + \
            2.0*self.y    * self.x**3 * pars[17] + \
            3.0*self.y**2 * self.x**2 * pars[18] + \
            4.0*self.y**3 * self.x    * pars[19] + \
            5.0*self.y**4 * pars[20]

        # fifth-order is probably enough for now!
        return zx, zy

    def tranpos(self):

        """Transforms the positions by the polyomials"""

        self.xtran = self.polyval2d(self.parsx)
        self.ytran = self.polyval2d(self.parsy)

    def getjacobian(self):

        """Populates the jacobian associated with the polynomial
transformations"""

        self.jac = np.zeros(( np.size(self.x), 2, 2 ))

        jxix, jxiy = self.jac2d(self.parsx)
        jetax, jetay = self.jac2d(self.parsy)

        self.jac[:,0,0] = jxix
        self.jac[:,0,1] = jxiy
        self.jac[:,1,0] = jetax
        self.jac[:,1,1] = jetay

    def trancov(self):

        """Transforms the covariance via the jacobian"""

        if np.size(self.jac) < 1:
            self.getjacobian()

        J = self.jac
        Jt = np.transpose(J, axes=(0,2,1))
        C = self.covxy

        self.covtran = np.matmul(J, np.matmul(C, Jt) )

    def propagate(self):

        """One-liner to propagate positions and covariances"""

        self.tranpos()
        self.getjacobian()
        self.trancov()

        self.populatexytran()
        
    def populatexytran(self):

        """Utility - updates the 2D xytran array"""
        
        # Updates [N,2] xytran array
        
        self.xytran[:,0] = self.xtran
        self.xytran[:,1] = self.ytran
        
    def nudgepos(self, dxarcsec=10., dyarcsec=10.):

        """Nudges the input positions by input amounts"""

        conv = 206265.
        if self.degrees:
            conv = 3600.

        self.x += dxarcsec / conv
        self.y += dyarcsec / conv
            
    def calcdeltas(self, dxarcsec=10., dyarcsec=10.):

        """Estimates deltas in the projected frame from Jacobian.dx"""

        if np.size(self.jac) < 4:
            return np.array([])

        # Produce delta-array in the same unit as the original
        # coordinates, assuming input in arcsec
        conv = 206265.
        if self.degrees:
            conv = 3600.
            
        dx = np.array([dxarcsec, dyarcsec])/conv
        dv = np.matmul(self.jac, dx)
        
        return dv

class Tan2equ(object):

    """Object handling the transformation of coordinates and covariances
from the tangent plane to the sky.

    (Arguments kindpoly, checkparsy, xmin, xmax, ymin, ymax, radec,
    covradec are for compatibility with other calls, and are currently
    ignored.)

    """

    # Convention: x, y => xi, eta
    
    def __init__(self, xi=np.array([]), eta=np.array([]), \
                 covxieta=np.array([]), \
                 pars=np.array([]), degrees=True, \
                 Verbose=True,
                 kindpoly=None, checkparsy=False, \
                 xmin=None, xmax=None, ymin=None, ymax=None, \
                 radec=None, covradec=None):

        self.x = xi
        self.y = eta
        self.covxy = covxieta
        
        self.pars = pars # the tangent point

        self.Verbose = Verbose # control variable

        # We store xmin, xmax, etc.
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        
        # Input coordinates are in degrees? (Alternate is radians)
        self.degrees = degrees
        self.conv2rad = 1.
        self.setconversion()
        
        # jacobian for transforming uncertainty
        self.jac=np.eye(2)
        self.initjac()

        # Go ahead and populate the jacobian on initialization
        self.setjacobian()

        # Output quantities
        self.xtran = np.array([])
        self.ytran = np.array([])
        self.covxytran = np.array([])

        # Some plot labels
        self.labelx = r'$\xi$'
        self.labely = r'$\eta$'
        self.labelxtran = r'$\alpha$'
        self.labelytran = r'$\delta$'

        # initialize the xytran convenience-view
        self.xytran = np.array([])
        self.initxytran()

    def updatedata(self, x=np.array([]), y=np.array([]), \
                   covxy=np.array([]), \
                   xy=np.array([]) ):

        """Ingests supplied data to populate x, y, covars. 

Inputs:


        x = [N] array of X-values. 

        y = [N] array of Y-values

        covxy = [N,2,2] array of XY covariances

        xy = [N,2] xy array. If set, supersedes x, y.

        
        Outputs:
        None - internal attributes self.x, self.y, self.covxy

"""

        # Positions
        if np.ndim(xy) == 2:
            self.x = xy[:,0]
            self.y = xy[:,1]
        else:
            self.x = np.copy(x)
            self.y = np.copy(y)
            
        # covariances. We parse here for matching size with the
        # positions before updating
        if np.ndim(covxy) != 3:
            return

        ndata = np.size(self.x)
        ncov = np.shape(covxy)[0]

        if ndata != ncov:
            return

        self.covxy = np.copy(covxy)

    def updatejacobian(self):

        """One-liner to update the jacobian"""

        # This is called from another method that uses
        # updatejacobian() as its call.
        self.setjacobian()
        
    def initxytran(self):

        """Initializes convenience-view xytran [N,2] using dimensions of input
data x"""

        self.xytran = np.zeros(( np.size(self.x), 2 ))
        
    def initjac(self):

        """Initializes the jacobian"""

        npoints = np.size(self.x)
        if npoints < 1:
            if self.Verbose:
                print("Tan2equ WARN - no datapoints. Initializing jacobian to identity")
            self.jac = np.eye(2)
            return
        
        self.jac = np.zeros(( npoints, 2, 2 ))
        self.jac[:,0,0] = 1.
        self.jac[:,1,1] = 1.
        
    def setconversion(self):

        """Sets the angular conversion factor to radians"""

        self.conv2rad = 1.
        if self.degrees:
            self.conv2rad = np.pi/180.

    def updatelimits(self, xmin=None, xmax=None, ymin=None, ymax=None):

        """Updates xmin, xmax, etc. attributes"""

        # For this object, is used mainly for compatibility
        
        self.xmin = np.copy(xmin)
        self.xmax = np.copy(xmax)
        self.ymin = np.copy(ymin)
        self.ymax = np.copy(ymax)
        
    def setjacobian(self):

        """Sets up the jacobian for the tangent plane to sky conversion"""

        self.jac = self.evaluatejac(self.x, self.y)

    def evaluatejac(self, x=np.array([]), y=np.array([]) ):

        """Computes the jacobian for input x, y"""

        if np.size(x) < 1 or np.size(y) < 1:
            return np.array([])
        
        # comparison on number of planes between data and jacobian
        # might come here.
        
        # Ensure input angles are in radians
        xi  = x * self.conv2rad
        eta = y * self.conv2rad
        alpha0 = self.pars[0] * self.conv2rad
        delta0 = self.pars[1] * self.conv2rad

        # Now we compute the four terms in the jacobian in turn:
        # dalpha / dxi
        denom00 = (np.cos(delta0) - eta*np.sin(delta0)) * \
            (1.0 + (xi/(np.cos(delta0) - eta*np.sin(delta0) ))**2 )
        J_ax = 1.0/denom00

        # dalpha / deta
        denom01 = xi**2 + (np.cos(delta0))**2 \
            - 2.0 * eta * np.cos(delta0) * np.sin(delta0) \
            + eta**2 * (np.sin(delta0))**2
        J_ay = xi*np.sin(delta0) / denom01

        # ddelta / dxi
        denom10 = (1.0 + xi**2 + eta**2) \
            * np.sqrt(xi**2 + (np.cos(delta0) - eta * np.sin(delta0) )**2 )

        J_dx = 0. - xi*( eta*np.cos(delta0) + np.sin(delta0)) / denom10

        # ddelta / deta
        J_dy = ((1.0 + xi**2)*np.cos(delta0) - eta*np.sin(delta0)) / denom10

        # now set up and populate the jacobian
        jac = np.zeros(( x.size, 2, 2 ))
        jac[:,0,0] = J_ax
        jac[:,0,1] = J_ay
        jac[:,1,0] = J_dx
        jac[:,1,1] = J_dy
        
        # ... and return this
        return jac
    
    def tranpos(self):

        """Maps instance's tangent plane coordinates onto equatorial. Updates self.xtran, self.ytran in the instance."""

        self.xtran, self.ytran = self.propxy(self.x, self.y)
        
    def propxy(self, x=np.array([]), y=np.array([])):

        """Maps input x, y from the tangent plane to equatorial coordinates. Returns xtran, ytran."""

        if np.size(x) < 1 or np.size(y) < 1:
            return np.array([]), np.array([])
        
        # Ensure the angles are computed in radians
        xi = x * self.conv2rad
        eta = y * self.conv2rad
        alpha0 = self.pars[0] * self.conv2rad
        delta0 = self.pars[1] * self.conv2rad

        gamma = np.cos(delta0) - eta*np.sin(delta0)
        alphaf = alpha0 + np.arctan(xi/gamma)
        deltaf = np.arctan(
            (eta*np.cos(delta0) + np.sin(delta0) ) /
            np.sqrt(xi**2 + gamma**2) )
        
        # Convert the equatorial positions back to the input system.
        xtran = alphaf / self.conv2rad
        ytran = deltaf / self.conv2rad

        return xtran, ytran
        
    def trancov(self):

        """Transforms instances' covariance matrices from tangent plane to
equatorial, does a little sanity checking on the covariance and jacobian. Updates self.covtran in the instance."""

        # Populate the jacobian if not already done
        #if np.size(self.jac) < 2:
        #    self.setjacobian()

        self.covtran = self.propcov(self.covxy, self.x, self.y)

    def propcov(self, C=np.array([]), x=np.array([]), y=np.array([]) ):

        """Transforms input covariance matrices from tangent plane to
equatorial, returning the transformed covariance matrices as an
[N,2,2] array."""

        if np.size(self.x) < 1 or np.size(y) < 1:
            return np.array([])

        J = self.evaluatejac(x, y)
        Jt = np.transpose(J,axes=(0,2,1))

        return np.matmul(J, np.matmul(C, Jt))
        
    def propagate(self):

        """One-liner to propagate the positions and covariances from tangent plane to equatorial"""

        self.tranpos()
        self.trancov()

        self.xytran[:,0] = self.xtran
        self.xytran[:,1] = self.ytran
        
    def updatetransf(self, pars=np.array([]) ):

        """One-liner to update the transformation and jacobian when the
pointing is changed"""

        # Don't do anything if bad parameters were passed
        if np.size(pars) != 2:
            return

        # Pass the parameters up and update the needed pieces. For
        # this class, that's not much.
        self.pars=np.copy(pars)
        self.setjacobian()

    def nudgepos(self, dxarcsec=10., dyarcsec=10.):

        """Nudges the input positions by dxarcsec, dyarcsec"""

        # Convert the nudge into degrees or radians as appropriate for
        # self.x, self.y
        conv = 206265.
        if self.degrees:
            conv = 3600.

        self.x += dxarcsec / conv
        self.y += dyarcsec / conv

        # recalculate the jacobian as appropriate for the nudged positions
        self.setjacobian()

    def calcdeltas(self, dxarcsec=10., dyarcsec=10.):

        """Estimates deltas in the projected frame from J.dx"""

        conv=206265.
        if self.degrees:
            conv = 3600.

        dx = np.array([dxarcsec, dyarcsec])/conv
        dv = np.matmul(self.jac, dx)

        return dv

    def getlabels(self):

        """Returns labels for plots (the coordinates of the tangent point)"""

        return [r'$\alpha_0$', r'$\delta_0$']
        
class Equ2tan(object):

    """Object handling the transformation of coordinates and covariances
from the sky to the tangent plane.

Inputs:

    x = [N] array of ra values

    y = [N] array of dec values

    covxy = [N,2,2] covariance (ra, dec) for each datapoint

    pars = [2] tangent point: (alpha_0, delta_0)

    degrees = all angles given in degrees (otherwise radians)

    Verbose = print screen output

    (Arguments kind, checkparsy, xmin, xmax, ymin, ymax, radcec,
    covradec are for compatibility with other calls, and are
    currently ignored)

    """

    # convention: x, y --> ra, dec

    def __init__(self, x=np.array([]), y=np.array([]), \
                 covxy=np.array([]), \
                 pars=np.array([]), degrees=True, \
                 Verbose=True, \
                 kindpoly=None, \
                 checkparsy=False, \
                 xmin=None, xmax=None, ymin=None, ymax=None, \
                 radec=None, covradec=None):

        self.x = x # ra
        self.y = y # dec
        self.covxy = covxy # cov ra, dec

        self.pars=pars # the tangent point

        self.Verbose = Verbose # control variable

        # input coordinates in degrees?
        self.degrees = degrees
        self.conv2rad = 1.
        self.setconversion()

        self.jac = np.eye(2)
        self.initjac()
        self.setjacobian() # set on initialization

        # output quantities
        self.xtran = np.array([])
        self.ytran = np.array([])
        self.covxytran = np.array([])
        
        # Some labels that'll come in handy when plotting, or when
        # reminding ourselves which quantity should be which
        self.labelx = r'$\alpha$'
        self.labely = r'$\delta$'
        self.labelxtran = r'$\xi$'
        self.labelytran = r'$\eta$'

        # initialize the xytran convenience-view
        self.xytran = np.array([])
        self.initxytran()

    def updatedata(self, x=np.array([]), y=np.array([]), \
                   covxy=np.array([]), \
                   xy=np.array([]) ):

        """Ingests supplied data to populate x, y, covars. 

Inputs:


        x = [N] array of X-values. 

        y = [N] array of Y-values

        covxy = [N,2,2] array of XY covariances

        xy = [N,2] xy array. If set, supersedes x, y.

        
        Outputs:
        None - internal attributes self.x, self.y, self.covxy

"""

        # Positions
        if np.ndim(xy) == 2:
            self.x = xy[:,0]
            self.y = xy[:,1]
        else:
            self.x = np.copy(x)
            self.y = np.copy(y)
            
        # covariances. We parse here for matching size with the
        # positions before updating
        if np.ndim(covxy) != 3:
            return

        ndata = np.size(self.x)
        ncov = np.shape(covxy)[0]

        if ndata != ncov:
            return

        self.covxy = np.copy(covxy)
        
    def initxytran(self):

        """Initializes convenience-view xytran [N,2] using dimensions of input
        data x"""

        self.xytran = np.zeros(( np.size(self.x), 2 ))
        
    def initjac(self):

        """Initializes the jacobian"""

        npoints = np.size(self.x)
        if npoints < 1:
            if self.Verbose:
                print("Equ2tan WARN - no datapoints. Initializing jacobian to identity")
            self.jac = np.eye(2)
            return
        
        self.jac = np.zeros(( npoints, 2, 2 ))
        self.jac[:,0,0] = 1.
        self.jac[:,1,1] = 1.
        
    def setconversion(self):

        """Sets the angular conversion factor to radians"""

        self.conv2rad = 1.
        if self.degrees:
            self.conv2rad = np.pi/180.

    def updatelimits(self, xmin=None, xmax=None, ymin=None, ymax=None):

        """Updates xmin, xmax, etc. attributes"""

        # For this object, is used mainly for compatibility
        
        self.xmin = np.copy(xmin)
        self.xmax = np.copy(xmax)
        self.ymin = np.copy(ymin)
        self.ymax = np.copy(ymax)
            
    def setjacobian(self):

        """Sets the jacobian for the equatorial to tangent plane conversion"""

        self.jac = self.evaluatejac(self.x, self.y)
        
    def evaluatejac(self, x=np.array([]), y=np.array([]) ):

        """Evaluates the jacobian at input x, y points"""

        if np.size(x) < 1 or np.size(y) < 1:
            return np.array([])

        alpha = x * self.conv2rad
        delta = y * self.conv2rad
        alpha0 = self.pars[0] * self.conv2rad
        delta0 = self.pars[1] * self.conv2rad

        # We have the same denominator for all four terms
        denom = ( np.cos(alpha-alpha0) * np.cos(delta) * np.cos(delta0) \
            + np.sin(delta)*np.sin(delta0) )**2

        # dxi/dalpha
        J_xia = np.cos(delta) * ( np.cos(delta) * np.cos(delta0) \
            + np.cos(alpha-alpha0) * np.sin(delta)*np.sin(delta0)) / denom

        # dxi/ddelta
        J_xid = 0. -np.sin(alpha-alpha0) * np.sin(delta0) / denom

        # deta/dalpha
        J_etaa = 0.5 * np.sin(alpha-alpha0) * np.sin(2.0*delta) / denom

        # deta/ddelta
        J_etad = np.cos(alpha-alpha0) / denom

        # now populate the jacobian
        jac = np.zeros(( x.size, 2, 2 ))
        jac[:,0,0] = J_xia
        jac[:,0,1] = J_xid
        jac[:,1,0] = J_etaa
        jac[:,1,1] = J_etad

        return jac
        
    def tranpos(self):

        """Maps instance's equatorial positions onto tangent plane, updating instance quantities self.xtran, self.ytran"""

        self.xtran, self.ytran = self.propxy(self.x, self.y)
        
    def propxy(self, x=np.array([]), y=np.array([]) ):
        
        """Maps input equatorial positions onto tangent plane. Returns the mapped x, y arrays."""

        if np.size(x) < 1 or np.size(y) < 1:
            return np.array([]), np.array([])
        
        # Ensure the angles are computed in radians
        alpha = x * self.conv2rad
        delta = y * self.conv2rad
        alpha0 = self.pars[0] * self.conv2rad
        delta0 = self.pars[1] * self.conv2rad

        denom = np.cos(alpha-alpha0) * np.cos(delta)*np.cos(delta0) \
            + np.sin(delta)*np.sin(delta0)

        xi = np.cos(delta)*np.sin(alpha-alpha0) / denom
        
        eta = (np.cos(delta0)*np.sin(delta) - \
            np.cos(alpha-alpha0)*np.cos(delta)*np.sin(delta0)) / denom

        # Return tangent plane coordinates including the
        # degrees/radians conversion
        xtran = xi / self.conv2rad
        ytran = eta / self.conv2rad

        return xtran, ytran
        
    def trancov(self):

        """Applies the transformation of instance's covariances from
equatorial to tangent plane, does a little sanity checking on the
jacobian. Updates self.covtran in the instance.
        """
        
        # Ensure the jacobian is appropriate
        if np.size(self.jac) < 2:
            self.setjacobian()

        self.covtran = self.propcov(self.covxy, self.x, self.y)
            
    def propcov(self, C=np.array([]), x=np.array([]), y=np.array([]) ):

        """Transforms input covariances C from equatorial to tangent plane. Returns the transformed covariances as an [N,2,2] array."""

        if np.size(x) < 1 or np.size(y) < 1:
            return np.array([])

        # Evaluate the jacobian at the input points
        J = self.evaluatejac(x, y)
        Jt = np.transpose(J,axes=(0,2,1))

        return np.matmul(J, np.matmul(C, Jt))

    def propagate(self):

        """One-liner to propagate the positions and covariances from equatorial to tangent plane"""

        self.tranpos()
        self.trancov()

        # update the 2D object for convenience when calling this
        self.xytran[:,0] = self.xtran
        self.xytran[:,1] = self.ytran
        
        
    def updatetransf(self, pars=np.array([]) ):

        """One-liner to update the transformation and jacobian when the pointing is changed"""

        # Check the parameters
        if np.size(pars) != 2:
            return

        self.pars = np.copy(pars)
        self.setjacobian()

    def nudgepos(self, dxarcsec=10., dyarcsec=10.):

        """Nudges the raw positions by input dxarcsec, dyarcsec"""

        # translate arcsec into the same system as the raw coords
        conv = 206265.
        if self.degrees:
            conv = 3600.

        self.x += dxarcsec / conv
        self.y += dyarcsec / conv

        # Re-evaluate the jacobian
        self.setjacobian()

    def calcdeltas(self, dxarcsec=10., dyarcsec=10.):

        """Calculates transformed deltas using J.dx"""

        conv=206265.
        if self.degrees:
            conv = 3600.

        dx = np.array([dxarcsec, dyarcsec])/conv
        dv = np.matmul(self.jac, dx)

        return dv

    def getlabels(self):

        """Returns list of labels to use for plots. This class only has two
parameters: the ra, dec of the tangent point.

        """

        return [r'$\alpha_0$', r'$\delta_0$']

class xy2equ(object):

    """Methods to propagate from XY coordinates through to equatorial.

Inputs:

    x, y - [N] - arrays of x, y position in the XY frame

    covxy - [N,2,2] - covariance array in the XY frame

    pars = [alpha0, delta0, parsxy] array of transformation parameters

    kindpoly = what kind of polynomial to use for XY --> tangent plane

    Verbose = control variable: print output to screen

    xmin, xmax, ymin, ymax = domain limits for the input data on the XY plane

    ---

    checkparsy = unused, included for compatibility

    radec = unused, included for compatibility

    covradec = unused, included for compatibility

"""

    def __init__(self, x=np.array([]), y=np.array([]), covxy=np.array([]), \
                 pars=np.array([]), kindpoly='Polynomial', \
                 Verbose=False, \
                 xmin=None, xmax=None, ymin=None, ymax=None, \
                 checkparsy=None, radec=None, covradec=None):

        # Control variable
        self.Verbose = Verbose
        
        # Set up the relevant parameters (including inds1d_6term)
        self.initpars()
        self.updatepars(pars)

        # Provide the attributes that calling methods expect
        self.x = x
        self.y = y
        self.covxy = covxy
        
        
        # Set up the transformation objects
        self.xy2tp = Poly(x, y, covxy, self.parsx, self.parsy, \
                          kind=kindpoly, checkparsy=False, \
                          Verbose=self.Verbose, \
                          xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)

        # Methods to transform from the tangent plane to equatorial
        self.tp2equ = Tan2equ(pars=self.tangentpoint, \
                              Verbose=self.Verbose)

        
        # Initialize a couple of needed things
        self.inittran()

        # Plot labels
        self.labelx = r'$X$'
        self.labely = r'$Y$'
        self.labelxtran = r'$\alpha$'
        self.labelytran = r'$\delta$'

        
    def initpars(self):

        """Initializes transformation parameters"""

        self.parsx = np.array([])
        self.parsy = np.array([])
        self.tangentpoint = np.array([])
        self.polyhasxy0 = True

        self.inds1d_6term = []
        
    def inittran(self):

        """Initialize the xytran and covxytran attributes"""

        self.covxytran = self.xy2tp.covxy * 0.
        self.xytran = self.xy2tp.xytran * 0.
        
    def updatepars(self, pars=np.array([]) ):

        """Updates instance parameters"""

        PV = Parvec(pars)
        
        self.parsx = PV.parsx
        self.parsy = PV.parsy
        self.tangentpoint = PV.tangentpoint
        self.polyhasxy0 = PV.hasxy0

        self.inds1d_6term = PV.inds1d_6term
        
    def tranpos(self):

        """Applies transformation from XY to equatorial, updating the
individual transformation objects as it does"""

        self.xy2tp.tranpos()
        self.tp2equ.x = self.xy2tp.xtran
        self.tp2equ.y = self.xy2tp.ytran

        self.tp2equ.tranpos()
        self.xtran = self.tp2equ.xtran
        self.ytran = self.tp2equ.ytran

    def trancov(self):

        """Transforms covariances from xy to equ"""

        # To ensure the positions going in to tp2equ.trancov are
        # correct, we propagate the positions into the tangent plane
        # as well. This *should* be redundant as long as all the calls
        # are first to tranpos() and then to trancov(). But that's the
        # kind of detail I can easily forget, so we sacrifice just a
        # little speed for safety.
        self.xy2tp.tranpos()
        self.tp2equ.x = self.xy2tp.xtran
        self.tp2equ.y = self.xy2tp.ytran
        
        self.xy2tp.trancov()
        self.tp2equ.covxy = self.xy2tp.covtran

        self.tp2equ.trancov()
        self.covtran = self.tp2equ.covtran

    def propagate(self):

        """Propagates positions and covariances from xy to equatorial"""

        self.tranpos()
        self.trancov()

        # 2024-09-04 just a little worried this seems to be necessary...
        self.xytran[:,0] = self.xtran
        self.xytran[:,1] = self.ytran

    def updatetransf(self, pars=np.array([]) ):

        """One-liner to update the transformation parameters for both
transformations

        """

        # Both the transformations have this check too. 
        if np.size(pars) < 1:
            return

        # update the parameters...
        self.updatepars(pars)

        parsxy = np.hstack(( self.parsx, self.parsy ))
        self.xy2tp.updatetransf(parsxy)

        # ... again, the jacobian for the sky piece depends on
        # coordinates. So we propagate those too.
        self.xy2tp.tranpos()
        self.tp2equ.x = self.xy2tp.xtran
        self.tp2equ.y = self.xy2tp.ytran
        self.tp2equ.updatetransf(self.tangentpoint)
        
        
    def getlabels(self):

        """Gets plot labels for the full transformation"""

        # Tangent point labels
        labelstp = self.tp2equ.getlabels()

        # Now the x, y polynomial labels. Need to be just a little
        # careful since the separate pointing arguments in the XY
        # plane will not usually be present.
        labelsx, labelsy = self.xy2tp.getlabels(retboth=True)

        # if the parameters do not include the pointing in the XY
        # frame, trim them down
        ilo=0
        if not self.polyhasxy0:
            ilo = 1

        # now return the labels
        return labelstp + labelsx[ilo::] + labelsy[ilo::]
        
class TangentPlane(object):

    """Methods to map positions from the sky (the catalog) and the focal
plane (X,Y data), and their covariances, onto the tangent plane for
comparison.

Inputs:

    x, y - [N] - arrays of x, y position in the XY frame

    covxy - [N,2,2] - covariance array in the XY frame

    pars = [alpha0, delta0, parsxy] array of transformation parameters

    kindpoly = what kind of polynomial to use for XY --> tangent plane

    radec = [N,2] array of RA, DEC target positions on the sphere

    covradec = [N,2,2] array of ra, dec covariances

    Verbose = control variable: print output to screen

    xmin, xmax, ymin, ymax = domain limits for the input data on the XY plane

    checkparsy = unused, included for compatibility

"""

    def __init__(self, x=np.array([]), y=np.array([]), covxy=np.array([]), \
                 pars=np.array([]), kindpoly='Polynomial', \
                 radec=np.array([]), covradec=np.array([]), \
                 Verbose=False, \
                 xmin=None, xmax=None, ymin=None, ymax=None, \
                 checkparsy=False):

        # control variables
        self.Verbose = Verbose
        
        # Distribute the parameters for the two transformations
        self.PV = Parvec(pars)
        self.polyhasxy0 = self.PV.hasxy0
        
        # Set up the transformation objects
        self.xy2tp = Poly(x, y, covxy, self.PV.parsx, self.PV.parsy, \
                          kind=kindpoly, xmin=xmin, xmax=xmax, \
                          ymin=ymin, ymax=ymax, checkparsy=False, \
                          Verbose=self.Verbose)

        self.eq2tp = Equ2tan(radec[:,0], radec[:,1], covradec, \
                             pars=self.PV.tangentpoint, degrees=True, \
                             Verbose=self.Verbose)
        

        # Which indices in the output parameter vector correspond to
        # the 6-term linear transformation
        self.inds1d_6term = np.copy(self.PV.inds1d_6term)
        
        # attributes expected by the likelihood object
        self.x = x
        self.y = y
        self.covxy = covxy

        self.initxytran()
        self.covtran = np.array([])

        self.initxytarg()
        self.covtarg = np.array([])

        # plot labels
        self.labelx = r'$X$'
        self.labely = r'$Y$'
        self.labelxtran = r'$\xi$'
        self.labelytran = r'$\eta$'
        
        # Propagate on initialization (WATCHOUT - might fail if blank
        # initialization)
        self.propagate()
        
    def initxytran(self):

        """Initializes xytran to same size as input data"""

        self.xytran = np.zeros(( np.size(self.x), 2 ))

    def initxytarg(self):

        """Initializes xytarg array"""

        self.xytarg = np.zeros(( np.size(self.x), 2 ))

        
    def updatetransf(self, pars=np.array([]) ):

        """One-liner to update the transformations onto the tangent space"""

        if np.size(pars) < 1:
            return

        # Update the parameters to the two transformation
        # objects. Note that this also updates the jacobians for the
        # uncertainties for each object via the methods in those objects.
        self.PV.ingestpars(pars)
        self.polyhasxy0 = self.PV.hasxy0

        self.xy2tp.updatetransf(np.hstack(( self.PV.parsx, self.PV.parsy )) )
        self.eq2tp.updatetransf(self.PV.tangentpoint)
        
    def tranpos(self):

        """Transforms source and target positions onto the tangent plane"""

        self.xy2tp.tranpos()
        self.eq2tp.tranpos()

        # The way we handle the transformed positions is still a bit
        # inefficient. Currently we have both the 1d and 2d versions
        # present, to be used by different routines. This really ought
        # to be systematized. For the moment we live with it...
        self.xtran = self.xy2tp.xtran
        self.ytran = self.xy2tp.ytran
        self.xtarg = self.eq2tp.xtran
        self.ytarg = self.eq2tp.ytran
        
        # Propagated from xy plane...
        self.xytran[:,0] = self.xtran
        self.xytran[:,1] = self.ytran

        # Propagated from the sphere
        self.xytarg[:,0] = self.xtarg
        self.xytarg[:,1] = self.ytarg

    def trancov(self):

        """Propagates the covariances from the xy and sphere to the tangent
plane"""

        # Probably need to be a bit careful when calling this to
        # ensure that the positions have been propagated first...
        self.xy2tp.trancov()
        self.eq2tp.trancov()

        # Now shunt into place
        self.covtran = self.xy2tp.covtran
        self.covtarg = self.eq2tp.covtran

    def propagate(self):

        """One-liner to propagate both the positions and covariances from the xy and sphere onto the tangent plane, as xytran, xytarg, respectively (and similar for covariances)"""

        self.tranpos()
        self.trancov()

    def getlabels(self):

        """Returns plot labels for parameters"""

        # Tangent point labels
        labelstp = self.eq2tp.getlabels()

        # Polynomial labels
        labelsx, labelsy = self.xy2tp.getlabels(retboth=True)

        # if the parameters do not include the pointing in the XY
        # frame, trim them down
        ilo=0
        if not self.polyhasxy0:
            ilo = 1

        # now return the labels
        return labelstp + labelsx[ilo::] + labelsy[ilo::]
        
class Sky(object):

    ### REPLACED by Tan2equ() and Equ2tan(), in order to have
    ### transformation objects that work exclusively in one direction.
    
    def __init__(self, possky=np.array([]), covsky=np.array([]), \
                 tpoint=np.array([]), \
                 postan=np.array([]), covtan=np.array([]) ):

        # positions, covariances on the sky
        self.possky = possky  # Nx2
        self.covsky = covsky # Nx2x2

        # tangent point, degrees
        self.tpoint=tpoint  # [2]

        # positions, covariances on the tangent plane
        self.postan = postan
        self.covtan = covtan

        # Jacobians for transforming uncertainties
        self.j2sky = np.array([])    # dalpha/dxi, etc.
        self.j2tan = np.array([])    # dxi/dalpha, etc.

        # Labels for transformed positions (when plotting)
        self.labelxtran = r'$\alpha$'
        self.labelytran = r'$\delta$'
        
    def sky2tan(self):

        """Converts sky coordinates to tangent plane coordinates. Input and output all in DEGREES."""

        # Unpack everything for readability later
        alpha0 = np.radians(self.tpoint[0])
        delta0 = np.radians(self.tpoint[1])

        alpha = np.radians(self.possky[:,0])
        delta = np.radians(self.possky[:,1])

        denom = np.cos(alpha-alpha0) * np.cos(delta)*np.cos(delta0) \
            + np.sin(delta)*np.sin(delta0)

        xi = np.cos(delta)*np.sin(alpha-alpha0) / denom
        
        eta = (np.cos(delta0)*np.sin(delta) - \
            np.cos(alpha-alpha0)*np.cos(delta)*np.sin(delta0)) / denom

        self.postan = self.possky*0.
        self.postan[:,0] = np.degrees(xi)
        self.postan[:,1] = np.degrees(eta)
        
    def tan2sky(self):

        """Converts tangent plane to sky coordinates. Input output all in DEGREES."""

        # Again, unpack everything for readability
        xi  = np.radians(self.postan[:,0])
        eta = np.radians(self.postan[:,1])

        alpha0 = np.radians(self.tpoint[0])
        delta0 = np.radians(self.tpoint[1])

        gamma = np.cos(delta0) - eta*np.sin(delta0)
        alphaf = alpha0 + np.arctan(xi/gamma)
        deltaf = np.arctan(
            (eta*np.cos(delta0) + np.sin(delta0) ) /
            np.sqrt(xi**2 + gamma**2) )

        # populate the instance
        self.possky = self.postan*0.
        self.possky[:,0] = np.degrees(alphaf)
        self.possky[:,1] = np.degrees(deltaf)

    def jac2sky(self):

        """Populates the Nx2x2 jacobian d(alpha, delta)/d(xi, eta) , which is
stored in object self.j2sky"""
        
        # unpack for readability
        xi  = np.radians(self.postan[:,0])
        eta = np.radians(self.postan[:,1])

        alpha0 = np.radians(self.tpoint[0])
        delta0 = np.radians(self.tpoint[1])

        # dalpha / dxi
        denom00 = (np.cos(delta0) - eta*np.sin(delta0)) * \
            (1.0 + (xi/(np.cos(delta0) - eta*np.sin(delta0) ))**2 )
        J_ax = 1.0/denom00

        # dalpha / deta
        denom01 = xi**2 + (np.cos(delta0))**2 \
            - 2.0 * eta * np.cos(delta0) * np.sin(delta0) \
            + eta**2 * (np.sin(delta0))**2
        J_ay = xi*np.sin(delta0) / denom01

        # ddelta / dxi
        denom10 = (1.0 + xi**2 + eta**2) \
            * np.sqrt(xi**2 + (np.cos(delta0) - eta * np.sin(delta0) )**2 )

        J_dx = 0. - xi*( eta*np.cos(delta0) + np.sin(delta0)) / denom10

        # ddelta / deta
        J_dy = ((1.0 + xi**2)*np.cos(delta0) - eta*np.sin(delta0)) / denom10

        # Populate the stack
        self.j2sky = np.zeros(( np.size(J_dx), 2, 2 ))
        self.j2sky[:,0,0] = J_ax
        self.j2sky[:,0,1] = J_ay
        self.j2sky[:,1,0] = J_dx
        self.j2sky[:,1,1] = J_dy
        
    def jac2tan(self):

        """Populates the Nx2x2 jacobian d(xi,eta)/d(alpha, delta), which is
stored in object self.j2tan"""

        # unpack for readability
        alpha = np.radians(self.possky[:,0])
        delta = np.radians(self.possky[:,1])

        alpha0 = np.radians(self.tpoint[0])
        delta0 = np.radians(self.tpoint[1])

        # We have the same denominator for all four terms
        denom = ( np.cos(alpha-alpha0) * np.cos(delta) * np.cos(delta0) \
            + np.sin(delta)*np.sin(delta0) )**2

        # dxi/dalpha
        J_xia = np.cos(delta) * ( np.cos(delta) * np.cos(delta0) \
            + np.cos(alpha-alpha0) * np.sin(delta)*np.sin(delta0)) / denom

        # dxi/ddelta
        J_xid = 0. -np.sin(alpha-alpha0) * np.sin(delta0) / denom

        # deta/dalpha
        J_etaa = 0.5 * np.sin(alpha-alpha0) * np.sin(2.0*delta) / denom

        # deta/ddelta
        J_etad = np.cos(alpha-alpha0) / denom

        # populate the stack
        self.j2tan = np.zeros(( np.size(J_xia),2,2 ))
        self.j2tan[:,0,0] = J_xia
        self.j2tan[:,0,1] = J_xid
        self.j2tan[:,1,0] = J_etaa
        self.j2tan[:,1,1] = J_etad

    def cov2sky(self):

        """Propagates the covariance matrices from tangent plane to sky"""

        J = self.j2sky
        Jt = np.transpose(J, axes=(0,2,1) )
        C = self.covtan

        JCJt = np.matmul(J, np.matmul(C, Jt) )
        self.covsky = JCJt

    def cov2tan(self):

        """Propagates the covariance matrices from sky to tangent plane"""

        J = self.j2tan
        Jt = np.transpose(J, axes=(0,2,1) )
        C = self.covsky

        JCJt = np.matmul(J, np.matmul(C, Jt) )
        self.covtan = JCJt

    def propag2sky(self, alpha0deg, delta0deg, \
                   postan=np.array([]), covtan=np.array([]), \
                   retvals=False):

        """One-liner to propagate tangent plane coordinates and covariances onto the sky, given input pointing. If retvals is True, the transformed positions and covariances are returned. Otherwise they are just updated in the instance."""

        # update the tangent point in radians
        self.tpoint=np.array([alpha0deg, delta0deg])

        # update the coords and covariances if they were supplied here
        # and if their lengths match
        if np.size(postan) > 0:
            self.postan = np.copy(postan)

        if np.abs(np.shape(covtan)[0] - np.shape(self.postan)[0]) < 1:
            self.covtan = np.copy(covtan)
        
        # Propagate the positions
        self.tan2sky()
        
        # Propagate the uncertainties
        self.jac2sky()
        self.cov2sky()

        if retvals:
            return self.possky, self.covsky

    def propag2tan(self, alpha0deg, delta0deg, \
                   possky=np.array([]), covsky=np.array([]), \
                   retvals=False):

        """One-liner to propagate equatorial coordinates and uncertainties onto the tangent plane. If retvals is True, the transformed positions and covariances are returned. Otherwise they are just updated in the instance."""

        # update the tangent point in radians
        self.tpoint=np.array([alpha0deg, delta0deg])

        # update the coords and covariances if they were supplied here
        # and if their lengths match
        if np.size(possky) > 0:
            self.possky = np.copy(possky)

        if np.abs(np.shape(covsky)[0] - np.shape(self.possky)[0]) < 1:
            self.covsky = np.copy(covsky)

        # Propagate the positions
        self.sky2tan()
        
        # Propagate the uncertainties
        self.jac2tan()
        self.cov2tan()

        if retvals:
            return self.postan, self.covtan

    def nudgepos(self, dxarcsec=10., dyarcsec=10.):

        """Nudges the tangent plane positions by input offsets"""

        self.postan[:,0] += dxarcsec / 3600.
        self.postan[:,1] += dyarcsec / 3600.

    def calcdeltas(self, dxarcsec=10., dyarcsec=10.):

        """Estimates deltas on the sky from the jacobian.dxi"""

        if np.size(self.j2sky) < 4:
            return

        # For this instance the Jacobian expects everything in
        # radians.
        dxi = np.array([dxarcsec, dyarcsec])/206265.
        dv = np.matmul(self.j2sky, dxi)

        # Converts back to degrees, since the sky coords are in degrees
        return np.degrees(dv)

    def tranpos(self):

        """Transforms tangent plane positions onto the sky using the same
naming convention as the Polynom() object. Updates quantities self.xtran, self.ytran"""

        self.tan2sky()
        self.xtran = self.possky[:,0]
        self.ytran = self.possky[:,1]

    def getlabels(self):

        """Returns labels for plots (the coordinates of the tangent point)"""

        return [r'$\alpha_0$', r'$\delta_0$']
        
# utility - return a grid of xi, eta points
def gridxieta(sidelen=2.1, ncoarse=11, nfine=41, llzero=False):

    """Returns a grid of points in xi, eta"""
    
    xv = np.linspace(0.-sidelen, sidelen, ncoarse, endpoint=True)
    yv = np.linspace(0.-sidelen, sidelen, nfine, endpoint=True)

    # set the minimum for each vector to zero?
    if llzero:
        xv -= np.min(xv)
        yv -= np.min(yv)
        
    xx, yy = np.meshgrid(xv, yv)
    xi = np.ravel(xx)
    eta = np.ravel(yy)

    # if ncoarse and nfine are the same, we do not need to double up
    if ncoarse != nfine:
        xi = np.hstack(( xi, np.ravel(yy) ))
        eta = np.hstack(( eta, np.ravel(xx) ))

    return xi, eta

    
def makecovars(npts=2, sigx=0.1, sigy=0.07, sigr=0.02, returnobj=False):

    """Utility - makes synthetic covariance matrices. If returnobj is
True, returns the entire CovStack object, otherwise just returns the
[nobjs, 2, 2] covariance array."""

    vstdxi = np.ones(npts)*sigx
    vstdeta = vstdxi * sigy/sigx
    vcorrel = np.ones(npts)*sigr
    CS = CovStack(vstdxi, vstdeta, r12=vcorrel, runOnInit=True)

    if returnobj:
        return CS
    else:
        return CS.covars
    
def makepars(deg=1, reverse=False, scale=1., rotdeg=0.):

    """Utility - makes sets of polynomial parameters for testing. Still a by-hand hack... If reverse is true, then these are the parameters going from [-1,1] domain to the output. In that case, the parameter 'scale' maps this domain onto the output domain."""

    # Rubbish by-hand hack for the moment
    
    parsx = np.array([ 120., 100., 20.])
    parsy = np.array([100., -10., 90.])

    detcd = 1.
    if reverse:
        cdmatrix = np.array([ [parsx[1], parsx[2]], \
                               [parsy[1], parsy[2]] ])
        cdinv = np.linalg.inv(cdmatrix)
        detcd = np.linalg.det(cdmatrix)/ (scale * 50.)

        cdinv = np.array([[1.1, -0.03],[0.04, 0.91]])

        cc = np.cos(np.radians(rotdeg))
        ss = np.sin(np.radians(rotdeg))
        rot = np.array([[cc, -ss], [ss, cc]])

        cd22 = np.matmul(cdinv,rot) * scale

        parsx = np.array([ 0.02, cd22[0,0], cd22[0,1]])
        parsy = np.array([-0.01, cd22[1,0], cd22[1,1]])
        
        #parsx = np.array([0.02, 1.1*scale, -0.03*scale])
        #parsy = np.array([-0.01, 0.04*scale, 0.91*scale])
        
        tpraw = np.array([parsx[0], parsy[0]])
        tpest = np.matmul(cdinv, tpraw)

        #parsx = np.array([0.02, cdinv[0,0], cdinv[0,1]])
        #parsy = np.array([0.05, cdinv[1,0], cdinv[1,1]])
        
    if deg > 1:
        xadd = np.array([15., 2., 1.]) /detcd
        yadd = np.array([7., 0.5, -4.]) /detcd
        parsx = np.hstack((parsx, xadd))
        parsy = np.hstack((parsy, yadd))

    if deg > 2:
        xadd = np.array([1., 2., 3., 4.])/detcd
        yadd = np.array([-4., -3., -2., -1.])/detcd

        parsx = np.hstack((parsx, xadd))
        parsy = np.hstack((parsy, yadd))

    return parsx, parsy

def fit6term(x, y, xi, eta, Verbose=False):

    """Utility - fits 6-term linear model to positions, interprets the
result in terms of human-readable parameters, returns the NormalEqs
and Stack2x2 objects for full access to results.

    """

    NE = NormalEqs(x, y, xi, eta, \
                   fitChoice='6term', xref=0., yref=0., flipx=False, \
                   Verbose=Verbose)
    NE.doFit()

    # Apply the fit to the input sample. Produces quantity NE.xiPred
    NE.applyTransfToFitSample()
    NE.xiPred = NE.xiPred.squeeze()
    
    # now translate the results into scales, rotation, skew
    SS = Stack2x2(NE.BMatrix)

    # returns the NE and SS objects
    return NE, SS

    
####### Methods that use the above follow

def checkdeltas(transf=None, dxarcsec=10., dyarcsec=10., showPlots=True, \
                cmap='viridis', symm=False, showpct=True):

    """Given a transformation object, checks the differences between the brute-force deltas and the Jacobian-obtained deltas"""

    if transf is None:
        return

    dv = transf.calcdeltas(dxarcsec, dyarcsec)

    # Now compute the deltas directly
    nudged = copy.deepcopy(transf)
    nudged.nudgepos(dxarcsec, dyarcsec)
    nudged.tranpos()

    # Hack to ensure the transformation object has the xtran, ytran
    # coordinates we expect here
    if not hasattr(transf, 'xtran'):
        transf.xtran = transf.possky[:,0]
        transf.ytran = transf.possky[:,1]
        transf.x = transf.postan[:,0]
        transf.y = transf.postan[:,1]
        detj = np.linalg.det(transf.j2sky)
    else:
        detj = np.linalg.det(transf.jac)
        
    dxbrute = nudged.xtran - transf.xtran
    dybrute = nudged.ytran - transf.ytran
    dvbrute = np.vstack(( dxbrute, dybrute )).T

    # Create delta of deltas array
    ddv = dv - dvbrute
    dmag = np.sqrt(dvbrute[:,0]**2 + dvbrute[:,1]**2)

    # views - our figure of merit
    sx = ddv[:,0]/dmag
    sy = ddv[:,1]/dmag
    
    if not showPlots:
        return

    # Are we showing as percent?
    if showpct:
        sx *= 100.
        sy *= 100.
    
    # symmetric limits for colorbars
    if symm:
        vminx = 0.-np.max(np.abs(sx))
        vmaxx = 0.+np.max(np.abs(sx))
        vminy = 0.-np.max(np.abs(sy))
        vmaxy = 0.+np.max(np.abs(sy))
    else:
        vminx = None
        vmaxx = None
        vminy = None
        vmaxy = None
        

    fig2=plt.figure(2)
    fig2.clf()
    ax1=fig2.add_subplot(223)
    ax2=fig2.add_subplot(224)
    ax0=fig2.add_subplot(221)

    # raw offsets?
    ax4=fig2.add_subplot(222)

    # Show the original positions. One more feature: if we are dealing
    # with outoput in equatorial coordinates, convert the magnitude
    # displayed here to arcsec and adjust the reporting accordingly
    magconv = 1.
    if hasattr(transf,'tpoint'):
        magconv = 3600.
    blah0=ax0.scatter(transf.x, transf.y, c=dmag*magconv, \
                      cmap=cmap, s=1)
    
    blah1=ax1.scatter(transf.xtran, transf.ytran, c=sx, \
                      cmap=cmap, s=1, \
                      vmin=vminx, vmax=vmaxx)

    blah2=ax2.scatter(transf.xtran, transf.ytran, c=sy, \
                      cmap=cmap, s=1, \
                      vmin=vminy, vmax=vmaxy)

    blah41 = ax4.scatter(transf.xtran, transf.ytran, s=1, \
                         c=detj,\
                         zorder=10)
    #blah42 = ax4.scatter(nudged.xtran, nudged.ytran, s=1, \
    #                     c='k', \
    #                     alpha=0.5, zorder=5)

    # colorbars
    cb0 = fig2.colorbar(blah0, ax=ax0)
    cb1 = fig2.colorbar(blah1, ax=ax1)
    cb2 = fig2.colorbar(blah2, ax=ax2)
    cb4 = fig2.colorbar(blah41, ax=ax4)

    
    ax0.set_xlabel(r'$\xi$, degrees')
    ax0.set_ylabel(r'$\eta$, degrees')

    # Some plot label carpentry
    labelx = r'$X$'
    labely = r'$Y$'
    if hasattr(transf, 'labelxtran'):
        labelx = transf.labelxtran
    if hasattr(transf, 'labelytran'):
        labely = transf.labelytran

    # For concatenation within latex strings
    labelxr = labelx.replace('$','')
    labelyr = labely.replace('$','')

    for ax in [ax1, ax2, ax4]:
        ax.set_xlabel(labelx)
        ax.set_ylabel(labely)

    # titles
    ax0.set_title(r"$|d\vec{%s}|$" % (labelxr) )
    if magconv > 1:
        ax0.set_title(r"$|d\vec{%s}|$, arcsec" % (labelxr) )
        
    ax1.set_title(r"$(d%s - d%s_{\rm J}) / |d\vec{%s}|$" \
                  % (labelxr, labelxr, labelxr))
    ax2.set_title(r"$(d%s - d%s_{\rm J}) / |d\vec{%s}|$" \
                  % (labelyr, labelyr, labelyr)) 

    if showpct:
        ax1.set_title(r"$100\times (d%s - d%s_{\rm J}) / |d\vec{%s}|$" \
                      % (labelxr, labelxr, labelxr))
        ax2.set_title(r"$100\times (d%s - d%s_{\rm J}) / |d\vec{%s}|$" \
                      % (labelyr, labelyr, labelxr))

    ax4.set_title('det(J)')
        
    # Show the input nudge
    ssup = r"$(\Delta \xi, \Delta\eta) = (%.1f, %.1f)$ arcsec" \
        % (dxarcsec, dyarcsec)

    # If the transformation object has a tangent point, show this too
    if hasattr(transf,'tpoint'):
        ssup = r"$(\Delta \xi, \Delta\eta) = (%.1f'', %.1f'')$, $(\alpha_0, \delta_0) = (%.1f, %.1f)$" %  (dxarcsec, dyarcsec, transf.tpoint[0], transf.tpoint[1])
    
    fig2.suptitle(ssup)
    fig2.subplots_adjust(hspace=0.5, wspace=0.5, top=0.85)
    
def testTransf(nobjs=5000, alpha0=35., delta0=35., sidelen=2.1, \
               showplots=True, \
               sigx=1.0, sigy=0.7, sigr=0.2, \
               usegrid=True, \
               dxarcsec=10., dyarcsec=10., showpct=True):


    # Example call:
    #
    # unctytwod.testTransf(usegrid=True, sidelen=2., dxarcsec=10., dyarcsec=0., delta0=57.9, showpct=False)

    
    # Construct a random set of xi, eta points for our
    # transformations. Use a square detector for convenience
    # halfrad = np.radians(sidelen)
    xieta = np.random.uniform(0.-sidelen, sidelen, (nobjs,2)) 

    if usegrid:
        xi, eta = gridxieta(sidelen, 11, 41)
        xieta = np.vstack((xi, eta)).T
        nobjs = np.size(xi)
        
    # construct our coordinate object
    SS = Sky(postan=xieta, tpoint=np.array([alpha0, delta0]) )

    # generate some covariances in the tangent plane. For testing,
    # default to uniform so that we can see how the transformation
    # impacts the covariances
    vstdxi = np.ones(nobjs)*sigx
    vstdeta = vstdxi * sigy/sigx
    vcorrel = np.ones(nobjs)*sigr
    CS = CovStack(vstdxi, vstdeta, r12=vcorrel, runOnInit=True)

    # pass the covariances arrays to the uncty2d object
    SS.covtan = np.copy(CS.covars)
    
    # convert tp to sky
    SS.tan2sky()

    # populate the jacobians
    SS.jac2sky()
    SS.jac2tan()

    # Now convert the covariance matrices from the tangent plane to the sky
    SS.cov2sky()

    # By this point we should have the Jacobian to the sky
    # populated. Run our checker to see how the deltas compare to each
    # other.
    checkdeltas(SS, dxarcsec, dyarcsec, showpct=showpct)
    
    ### Check whether the jacobians really are the inverses of each
    ### other...
    Jsky = SS.j2sky
    Jinv = np.linalg.inv(SS.j2tan)

    print("Inversion check - sky vs inv(tan):")
    print(Jsky[0])
    print(Jinv[0])

    Jtan = SS.j2tan
    Jsin = np.linalg.inv(SS.j2sky)
    
    print("Inversion check - tan vs inv(sky):")
    print(Jtan[0])
    print(Jsin[0])

    print("============")
    
    print("Covariances on the sky:", SS.covsky.shape)

    # Try converting back again... do we get the same as the input?
    SS.cov2tan()
    
    print("INFO: input row 0:", CS.covars[0])
    print("INFO: conv row 0:", SS.covsky[0])
    print("INFO: back row 0:", SS.covtan[0])


    ### Now try the one-liner
    TT = Sky()
    TT.propag2sky(alpha0, delta0, xieta, CS.covars)

    print("One-liner check:")
    print(SS.covsky[0])
    print(TT.covsky[0])
    print("============")

    ### Try the one-liner in the other direction
    RR = Sky()
    RR.propag2tan(alpha0, delta0, SS.possky, SS.covsky)

    print("One-liner check, other direction:")
    print(SS.covtan[0])
    print(RR.covtan[0])
    print("============")

    
    # compute the determinants
    det2sky = np.linalg.det(SS.j2sky)
    det2tan = np.linalg.det(SS.j2tan)

    # so that we can conveniently divide out the cos(delta) when
    # plotting
    cosdec = np.cos(np.radians( SS.possky[:,1] ))

    print("testTransf INFO -- covtan shape:",SS.covtan.shape)
    print(SS.covtan[0])
    print(SS.j2sky.shape)
    print(SS.j2tan.shape)
    print(SS.j2sky[0])
    
    if not showplots:
        return
    
    fig1 = plt.figure(1)
    fig1.clf()
    ax1 = fig1.add_subplot(221)
    ax2 = fig1.add_subplot(222)

    blah1 = ax1.scatter(SS.postan[:,0], SS.postan[:,1], s=2, \
#                        c=SS.j2sky[:,1,1] )
                        c = det2sky * cosdec ) 
    blah2 = ax2.scatter(SS.possky[:,0], SS.possky[:,1], s=2, \
#                        c=SS.j2tan[:,1,1] )
                        c = det2tan / cosdec )
    cb1 = fig1.colorbar(blah1, ax=ax1)
    cb2 = fig1.colorbar(blah2, ax=ax2)

    ax1.set_xlabel(r'$\xi$, degrees')
    ax1.set_ylabel(r'$\eta$, degrees')
    ax2.set_xlabel(r'$\alpha$, degrees')
    ax2.set_ylabel(r'$\delta$, degrees')

    ax1.set_title(r'$\left|\frac{\partial(\alpha,\delta)}{\partial(\xi, \eta)}\right|\cos(\delta)$')
    ax2.set_title(r'$|\frac{\partial(\xi,\eta)}{\partial(\alpha, \delta)}|/\cos(\delta)$')
    
    fig1.subplots_adjust(hspace=0.4, wspace=0.4)


def testpoly(sidelen=2.1, ncoarse=15, nfine=51, \
             showplots=True, \
             sigx=1.0, sigy=0.7, sigr=0.2, \
             symm=False, cmap='viridis', \
             dxarcsec=10., dyarcsec=10., degrees=True):

    """Test the propagation through a polynomial"""

    # Example call:
    #
    # unctytwod.testpoly(dxarcsec=10., dyarcsec=-10.)
    
    # Create the grid of points
    xi, eta = gridxieta(sidelen, ncoarse, nfine)

    # concatenate these into the N,2 array we expect
    xieta = np.vstack((xi, eta)).T
    
    # transformation parameters. While testing I'll just write out
    # some examples here. Consider making this more systematic later
    # on...
    parsx = [ 10., 10., 2.]
    parsy = [-5., -1., 9.]

    # add some curvature via quadratic
    parsx = parsx + [1.5, 0.2, 0.1]
    parsy = parsy + [0.7, 0.05, -0.4]

    # Now make this really curved...
    parsx = parsx +  [0.1, 0.2, 0.3, 0.4]
    parsy = parsy +  [-0.4, -0.3, -0.2, -0.1]
    
    # Covariances in the original frame
    vstdxi = np.ones(np.size(xi))*sigx
    vstdeta = vstdxi * sigy/sigx
    vcorrel = np.ones(np.size(xi))*sigr
    CS = CovStack(vstdxi, vstdeta, r12=vcorrel, runOnInit=True)
    
    # Create the instance and use it
    PP = Polynom(xieta, CS.covars, parsx, parsy)
    PP.propagate()

    # try our deltas-checker
    checkdeltas(PP, dxarcsec, dyarcsec, cmap=cmap, symm=symm)
    
    if not showplots:
        return
    
    fig1 = plt.figure(1)
    fig1.clf()
    ax1 = fig1.add_subplot(221)
    ax2 = fig1.add_subplot(222)

    # plot the original coordinates
    blah1 = ax1.scatter(xi, eta, s=1)
    ax1.set_xlabel(r'$\xi$')
    ax1.set_ylabel(r'$\eta$')
    ax1.set_title('raw')
    
    # plot the transformed coordinates
    blah2 = ax2.scatter(PP.xtran, PP.ytran, s=1)
    ax2.set_xlabel(r'$X$')
    ax2.set_ylabel(r'$Y$')
    ax2.set_title('transformed')

    # did that produce sensible output?
    print(PP.covxy[0])
    print(PP.covtran[0])

    # because np.matmul works plane-by-plane, the test of how delta-x
    # compares with jac x delta xi is pretty easy to do once you have
    # the jacobian in place. Return to this tomorrow.


def testpolycoefs(nterms=10, Verbose=True, \
                  showcheb=True, \
                  xtest = 0.2, ytest=0.2):

    """Tests the polycoeffs functionality"""

    p = np.arange(nterms)
    PC = Polycoeffs(p, Verbose=Verbose)
    print("Input params:", p)
    print("Degree:", PC.deg)
    print("i-indices:", PC.i)
    print("j-indices:", PC.j)
    print("2D coeffs array:")
    print(PC.p2d) # gets a separate line for nice printing

    # try the one-liner
    dum = PC.getcoeffs2d(p+1)

    print("One-liner call-return with p + 1 as input:")
    print(dum)

    # Now try differentiating this
    cderx = polynomial.polynomial.polyder(dum, 1, 1, 0)
    cdery = polynomial.polynomial.polyder(dum, 1, 1, 1)

    print("One-liner differentiated wrt x, padded")
    print(np.pad(cderx, [[0,1],[0,0]] )  )

    print("One-liner differentiated wrt y, padded")
    print(np.pad(cdery,[[0,0],[0,1]] )  )

    # Try a polynomial object
    PP = Poly()
    dx, dy = PP.derivcoeffs(dum)

    print("Using the polynomial object:")
    print("d/dx:")
    print(dx)

    print("d/dy:")
    print(dy)
    
    # what happens with chebyshev? Try it!
    print("Interpreting coeffs as chebyshev and differentiating:")
    chderx = polynomial.chebyshev.chebder(dum, 1, 1, 0)
    chdery = polynomial.chebyshev.chebder(dum, 1, 1, 1)

    print("Chebder wrt x")
    print(chderx)

    print("Chebder wrt y")
    print(chdery)

    
    if not showcheb:
        return
    
    # Now try playing with numpy's polynomial methods.
    cheb2d = polynomial.chebyshev.chebval2d(xtest, ytest, PC.p2d) 
    
    print("INFO - chebval2d at %.2f, %.2f gives %.2f" % (xtest, ytest, cheb2d) )

    # Now try the 1D object. Do we trust the domains?
    cheb1 = polynomial.chebyshev.chebval(xtest, PC.p2d[0])

    C = getattr(polynomial, 'Chebyshev')

    Cheb = C(PC.p2d[0], domain=[-1., 1.])
    
    print("INFO - chebval1d:")
    print("Using coeffs", PC.p2d[0])
    print("chebval at x=%.2f gives " % (xtest), cheb1)
    print("Cheb gives" , Cheb(xtest) )


def testconvenience(sidelen=2.1, ncoarse=15, nfine=51, \
                    deg=3, kind='Polynomial', Verbose=True, \
                    showplots=False, \
                    sigx=0.1, sigy=0.07, sigr=0.02, \
                    dxarcsec=10., dyarcsec=10., \
                    cmap='viridis', showpct=True, reverse=False):

    """Tests the convenience polynomial methods in numpy."""

    # Synthetic datapoints (if reverse, pretend this is a camera)
    xi, eta = gridxieta(sidelen, ncoarse, nfine, llzero=reverse)
    xieta = np.vstack((xi, eta)).T
    nobjs = np.size(xi)

    # Synthetic covariances in the original frame
    vstdxi = np.ones(np.size(xi))*sigx
    vstdeta = vstdxi * sigy/sigx
    vcorrel = np.ones(np.size(xi))*sigr
    CS = CovStack(vstdxi, vstdeta, r12=vcorrel, runOnInit=True)
    covsxieta = CS.covars
    
    parsx, parsy = makepars(deg=deg, reverse=reverse)
    
    # Access the poly domain
    xmin = None
    xmax = None
    ymin = None
    ymax = None

    # try generating with "wrong" parameters first then updating them
    parsxr = parsx[::-1]
    parsyr = parsy[::-1]
    
    # now create the polynomial object. We deliberately use the wrong
    # parameters (but with correct lengths) for initialization so that
    # we can ensure the update step later on works.
    PP = Poly(xi, eta, covsxieta, parsxr, parsyr, \
              kind=kind, Verbose=Verbose, \
              xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, \
              degrees=not(reverse), xisxi=not(reverse))

    # Try updating the parameters after initialization. Does this
    # work?
    PP.updatetransf(np.hstack(( parsx, parsy )) )
    
    # Translate the raw positions and covariances from input to target
    # frame, including working out the jacobian terms
    PP.propagate()
    
    # Nudge the positions BEFORE sending them to the object, to avoid
    # issues to do with points being shifted outside the domain.
    conv = 3600.
    if reverse:
        conv = 1.
        
    xinudged = xi + dxarcsec / conv
    etanudged = eta + dyarcsec / conv

    PPn = Poly(xinudged, etanudged, covsxieta, parsx, parsy, \
               kind=kind, Verbose=Verbose, \
               xmin=PP.xmin, xmax=PP.xmax, ymin=PP.ymin, ymax=PP.ymax)
    PPn.propagate()

    ## ... or we can nudge within the object. Uncomment the lines below
    ## to do so.
    #PPn = copy.copy(PP)
    #PPn.nudgepos(dxarcsec, dyarcsec)
    #PPn.propagate()
    ## #print(PPP.xtran[0:5], PPn.xtran[0:5])

    # Now we create the diagnostics
    
    # Deltas estimated from the jacobian
    dv = PP.calcdeltas(dxarcsec, dyarcsec)

    dxbrute = PPn.xtran - PP.xtran
    dybrute = PPn.ytran - PP.ytran
    dvbrute = np.vstack(( dxbrute, dybrute )).T

    # create deltas of deltas array
    ddv = dv - dvbrute
    dmag = np.sqrt(dxbrute**2 + dybrute**2)

    detj = np.linalg.det(PP.jac)
    
    # views - our figure of merit
    sx = ddv[:,0]/dmag
    sy = ddv[:,1]/dmag
    
    if not showplots:
        return
    
    # OK how does that look...
    fig3=plt.figure(3)
    fig3.clf()
    ax1=fig3.add_subplot(221)
    ax2=fig3.add_subplot(222)
    ax3=fig3.add_subplot(223)
    ax4=fig3.add_subplot(224)

    # conversion factor for the fractional deltas
    sconv = 1.
    if showpct:
        sconv = 100.
    
    blah1 = ax1.scatter(PP.x, PP.y, c=detj, cmap=cmap, s=1)
    blah2 = ax2.scatter(PP.xtran, PP.ytran, c=dmag, cmap=cmap, s=1)
    blah3 = ax3.scatter(PP.xtran, PP.ytran, c=sx*sconv, cmap=cmap, s=1)
    blah4 = ax4.scatter(PP.xtran, PP.ytran, c=sy*sconv, cmap=cmap, s=1)

    # just a bit of string carpentry needed
    sxrep = PP.labelxtran.replace('$','')
    syrep = PP.labelytran.replace('$','')

    # Units for the deltas
    sunit = '(")'
    if not PP.degrees:
        sunit = '(pix)'
    
    ax2.set_title(r'$|d\vec{%s}|$ %s' % (sxrep, sunit))
    ax1.set_title(r'det(J)')

    stitl4 = r'$(d%s - d%s_J)/|d\vec{%s}|)$' % (syrep, syrep, sxrep)
    if showpct:
        stitl4 = r'$100\times(d%s - d%s_J)/|d\vec{%s}|)$' \
            % (syrep, syrep, sxrep)
        
    stitl3 = stitl4.replace(syrep,sxrep)
    
    ax3.set_title(stitl3)
    ax4.set_title(stitl4)
    
    cb1 = fig3.colorbar(blah1, ax=ax1)
    cb2 = fig3.colorbar(blah2, ax=ax2)
    cb3 = fig3.colorbar(blah3, ax=ax3)
    cb4 = fig3.colorbar(blah4, ax=ax4)

    # inherit the label from the object
    ax1.set_xlabel(PP.labelx)
    ax1.set_ylabel(PP.labely)

    for ax in [ax2, ax3, ax4]:
        ax.set_xlabel(PP.labelxtran)
        ax.set_ylabel(PP.labelytran)
    
    # some cosmetic updating
    fig3.subplots_adjust(hspace=0.5, wspace=0.5, top=0.85)

    # show the input offset. We are in danger of repeating ourselves
    # from a previous diagnostic plot here!
    ssup = r'$(\Delta \xi, \Delta\eta)=(%.1f, %.1f)$ %s' \
        % (dxarcsec, dyarcsec, sunit.replace('(','').replace(')',''))

    fig3.suptitle("%s(%i), %s" % (PP.kind, PP.pars2x.deg, ssup))
    
    ## ... and take a look at the resulting object(s)
    #print(PP.polx, PP.polx.domain)
    #print(PP.poly, PP.poly.domain)

def testsky(sidelen=2.1, ncoarse=15, nfine=51, \
            alpha0=35., delta0=35.,
            usegrid=True, showplots=True, showpct=True, \
            sigx=0.1, sigy=0.07, sigr=0.02, \
            Verbose=True, \
            dxarcsec=10., dyarcsec=10., cmap='viridis', \
            deltaback=False, returnwithposan=False):

    """Test routines for the one-directional Tan2equ() and Equ2tan(). Example calls:

    # produce a quiver plot showing the impact on (xi, eta) of
    # changing the pointing by dxarcsec, dyarcsec
    unctytwod.testsky(sidelen=5., delta0=35.0, dxarcsec=100., dyarcsec=100., cmap='inferno', deltaback=True, ncoarse=31, nfine=31)

    # produce a plot showing the difference between brute
    # force-computed deltas and those computed via the jacobian
    unctytwod.testsky(sidelen=5., delta0=35.0, dxarcsec=10., dyarcsec=10., cmap='inferno')

    """

    # Adapted from testTransf() above.

    # create xi, eta positions
    xi, eta = gridxieta(sidelen, ncoarse, nfine)

    # generate some covariances in the tangent plane. For testing,
    # default to uniform so that we can see how the transformation
    # impacts the covariances
    covs = makecovars(np.size(xi), sigx, sigy, sigr, returnobj=False)
    
    # tangent point
    tpoint = np.array([alpha0, delta0])
    
    # now set up the tan2sky object, transform positions and covariances
    T2E = Tan2equ(xi, eta, covs, tpoint, Verbose=Verbose)
    T2E.propagate()

    # Now we create a new object to go in the opposite direction and
    # "undo" the changes.
    E2T = Equ2tan(T2E.xtran, T2E.ytran, T2E.covtran, tpoint, Verbose=Verbose)
    E2T.propagate()

    # Another useful test: shift positions, transform back to xi, eta,
    # and find the deltas
    alpha0nudged = alpha0 + dxarcsec/3600.
    delta0nudged = delta0 + dyarcsec/3600.
    E2Tn = Equ2tan(np.copy(T2E.xtran), np.copy(T2E.ytran), T2E.covtran, \
                   np.array([alpha0nudged, delta0nudged]), Verbose=Verbose)
    #E2Tn.nudgepos(dxarcsec, dyarcsec)
    E2Tn.propagate()
    
    # Create some figures of merit.
    #
    # The determinants of the original covariances and the
    # transformed-back covariances. Not very interesting if the
    # originals are all the same value...
    detcovxi = np.linalg.det(T2E.covxy)
    detcovback = np.linalg.det(E2T.covtran)

    if not returnwithposan:
        print("Round-trip differences in det(cov): %.3e to %.3e" \
              % (np.min(detcovback - detcovxi), \
                 np.max(detcovback - detcovxi)) )
    
    # Consider refactoring this set of nudge-based diagnostics into
    # another method, since I'm starting to repeat myself in all these
    # test routines...

    detj=np.linalg.det(T2E.jac)
    
    # Nudge positions, recompute, and recalculate
    T2En = copy.deepcopy(T2E)
    T2En.nudgepos(dxarcsec, dyarcsec)
    T2En.propagate()
    dxbrute = T2En.xtran - T2E.xtran
    dybrute = T2En.ytran - T2E.ytran
    dvbrute = np.vstack((dxbrute, dybrute)).T
    dmag = np.sqrt(dxbrute**2 + dybrute**2)
    
    # compute the deltas with the original points
    dv = T2E.calcdeltas(dxarcsec, dyarcsec)

    # our figure of merit
    ddv = dv - dvbrute
    sx = ddv[:,0]/dmag
    sy = ddv[:,1]/dmag

    #print(np.min(np.abs(sx)), np.max(np.abs(sx)), np.mean(np.abs(sx)))
    #print(np.min(dmag), np.max(dmag))

    if not showplots:
        return

    if deltaback:

        # fit the transformation, returning the fit objects
        NE, SS = fit6term(E2T.xtran, E2T.ytran, E2Tn.xtran, E2Tn.ytran, \
                          Verbose=not(returnwithposan))

        # Return and report the position angle?
        if returnwithposan:
            return SS.rotDeg*3600.
        
        print("testsky pointing INFO - 6-term parameters:")
        print("==========================================")
        print("xi0: %f arcsec" % (NE.xiRef[0]*3600.))
        print("eta0: %f arcsec" % (NE.xiRef[1]*3600.))
        print("sx: %f" % (SS.sx))
        print("sy: %f" % (SS.sy))
        print("Rotation: %f arcsec" % (SS.rotDeg * 3600.))
        print("Skew: %f mas" % (SS.skewDeg * 3.6e6))
        print("======")

        # Deltas due to pointing shift
        deltaxi = E2Tn.xtran - E2T.xtran
        deltaeta = E2Tn.ytran - E2T.ytran

        # Removal of 6-term fit
        residxi  = E2Tn.xtran - NE.xiPred[:,0]
        resideta = E2Tn.ytran - NE.xiPred[:,1]

        # if we're looking at the result of a pointing shift, set up a
        # separate figure.
        dxisho = deltaxi*3600. + dxarcsec*np.cos(np.radians(delta0))
        detasho = deltaeta * 3600. + dyarcsec

        # arrow magnitudes
        deltamag = np.sqrt(dxisho**2 + detasho**2)
        xrange = np.max(E2T.xtran) - np.min(E2T.xtran)
        quivscale = 0.1*xrange/np.max(deltamag)

        # For the scale, use a quantile
        ql = np.quantile(deltamag, 0.9)

        # if this is less than 0.01 arcsec, switch to milliarcsec
        unitsho = '"'
        if ql < 0.1:
            dxisho *= 1000.
            detasho *= 1000.
            deltamag *= 1000.
            ql *= 1000.
            unitsho=' mas'

        # Quiver plot with the pointing offset
        fig6 = plt.figure(6, figsize=(6,6))
        fig6.clf()
        ax6 = fig6.add_subplot(111)
        blah6 = ax6.quiver(E2T.xtran, E2T.ytran, dxisho, detasho, \
                           color='#00274C', \
                           angles='xy', scale_units='xy', units='xy', \
                           scale=None)#quivscale)

        # For the scale, use a quantile
        qk = ax6.quiverkey(blah6, 0.05, 0.97, U=ql, label='%.1f%s' \
                           % (ql, unitsho), \
                           labelpos='E')

        ## Experiment to locate the approximate center of rotation
        ## [xi_0, eta_0]
        #dum66 = ax6.scatter([0.-NE.xiRef[0]], [0.-NE.xiRef[1]], marker='x')
        ## dalpha.tan(delta0) seems to be a bit closer...
        #dum67 = ax6.scatter(dxarcsec*np.tan(delta0)/3600., \
        #                    0.-NE.xiRef[1], marker='+')
        
        # quiver plot with the residuals

        # slight hack: use the same conversion as above
        convresid = 3600.
        if ql < 0.1:
            converesid *= 1000.
        rxisho = residxi * convresid
        retasho = resideta * convresid
        residmag = np.sqrt(rxisho**2 + retasho**2)
        qr = np.quantile(residmag, 0.9)
        
        fig7 = plt.figure(7, figsize=(6,6))
        fig7.clf()
        ax7=fig7.add_subplot(111)
        blah7 = ax7.quiver(E2T.xtran, E2T.ytran, rxisho, retasho, \
                           color='#9A3324',\
                           angles='xy', scale_units='xy', units='xy', \
                           scale=None)#quivscale)

        qkr = ax7.quiverkey(blah7, 0.05, 0.97, U=qr, label='%.2e%s' \
                            % (qr, unitsho), \
                            labelpos='E')

        # Figure labels and titles come here.
        
        # set the axes ranges and labels
        for ax in [ax6, ax7]:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()

            ax.set_xlim(xlim*np.repeat(1.1,2))
            ax.set_ylim(ylim*np.repeat(1.1,2))
        
            ax.set_xlabel(E2T.labelxtran)
            ax.set_ylabel(E2T.labelytran)

        supquiv = r'$(\Delta \alpha_0, \Delta \delta_0) = (%.1f, %.1f)$"' \
            % (dxarcsec, dyarcsec)

        skind = r'$(\alpha_0, \delta_0)=(%.1f^{\circ}, %.1f^{\circ})$' \
            % (E2T.pars[0], E2T.pars[1])

        # Title for axis 6
        stitl6 = r'Arrows: $(\Delta \xi, \Delta \eta) - (-\cos(\delta_0) \Delta \alpha_0, - \Delta \delta_0)$%s' % (unitsho)

        stitl7 = r'Arrows: $(\Delta \xi, \Delta \eta)$ - 6term$(\Delta \xi, \Delta \eta)$%s' % (unitsho)
        
        ax6.set_title(stitl6)
        ax7.set_title(stitl7)

        # set the supertitles
        for fig in [fig6, fig7]:
            fig.suptitle('%s, %s' % (supquiv, skind))
        
        #### arrow plot finishes here.
        return
        
    # conversion factor for the fractional deltas
    sconv = 1.
    if showpct:
        sconv = 100.
    
    fig1=plt.figure(1)
    fig1.clf()
    ax1 = fig1.add_subplot(221)
    ax2 = fig1.add_subplot(222)
    ax3 = fig1.add_subplot(223)
    ax4 = fig1.add_subplot(224)

    # hack for what we're plotting on the fourth axis
    sy4 = sy*sconv
    if deltaback:
        sy4 = deltaxi * 3600.  # in arcsec
    
    blah1 = ax1.scatter(T2E.x, T2E.y, s=1, c=detj, cmap=cmap)
    blah2 = ax2.scatter(T2E.xtran, T2E.ytran, s=1, c=dmag*3600., cmap=cmap)

    # what we show on the last row depends on what we're doing
    if not deltaback:
        blah3 = ax3.scatter(E2T.x, E2T.y, s=1, c=sx*sconv, cmap=cmap)
        blah4 = ax4.scatter(E2T.xtran, E2T.ytran, s=1, c=sy*sconv, cmap=cmap)
    else:
        blah3 = ax3.scatter(E2T.xtran, E2T.ytran, s=1, c=deltaxi*3600., \
                            cmap=cmap)
        blah4 = ax4.scatter(E2T.xtran, E2T.ytran, s=1, c=deltaeta*3600., \
                            cmap=cmap)
        
    # This was used when debugging the deltas
    #blah4 = ax4.hist(sx, bins=100, log=True)
    #blah42 = ax4.hist(sy, bins=100, log=True)
    
    cb1 = fig1.colorbar(blah1, ax=ax1)
    cb2 = fig1.colorbar(blah2, ax=ax2)
    cb3 = fig1.colorbar(blah3, ax=ax3)
    cb4 = fig1.colorbar(blah4, ax=ax4)
    
    ax1.set_xlabel(T2E.labelx)
    ax1.set_ylabel(T2E.labely)
    ax2.set_xlabel(T2E.labelxtran)
    ax2.set_ylabel(T2E.labelytran)

    if not deltaback:
        ax3.set_xlabel(E2T.labelx)
        ax3.set_ylabel(E2T.labely)
    else:
        ax3.set_xlabel(E2T.labelxtran)
        ax3.set_ylabel(E2T.labelytran)

    ax4.set_xlabel(E2T.labelxtran)
    ax4.set_ylabel(E2T.labelytran)

    # string carpentry for plots again
    sxrep = T2E.labelxtran.replace('$','')
    syrep = T2E.labelytran.replace('$','')

    ax2.set_title(r'$|d\vec{%s}|$ (")' % (sxrep))
    ax1.set_title(r'det(J)')

    stitl4 = r'$(d%s - d%s_J)/|d\vec{%s}|)$' % (syrep, syrep, sxrep)
    if showpct:
        stitl4 = r'$100\times(d%s - d%s_J)/|d\vec{%s}|)$' \
            % (syrep, syrep, sxrep)
        
    stitl3 = stitl4.replace(syrep,sxrep)
    if not deltaback:
        ax3.set_title(stitl3)
        ax4.set_title(stitl4)
    else:
        ax3.set_title(r'$\Delta \xi$ (")')
        ax4.set_title(r'$\Delta \eta$ (")')

    # What are we showing here?
    stitl = r'$(\Delta \xi - \Delta \alpha_0 \cos(\delta_0)$, $(\Delta \eta - \Delta \delta_0)$'

    # some cosmetics
    ssup = r'$(\Delta \xi, \Delta\eta)=(%.1f$",$%.1f$")' \
        % (dxarcsec, dyarcsec)
    
    skind = r'$(\alpha_0, \delta_0)=(%.1f^{\circ}, %.1f^{\circ})$' \
        % (T2E.pars[0], T2E.pars[1])
    fig1.suptitle("%s; %s" % (ssup, skind))
    fig1.subplots_adjust(hspace=0.5, wspace=0.5, top=0.85)


def wraptestsky(dxarcsec=10., dyarcsec=0., sidelen=2.1, \
                ncoarse=51, nfine=51, alpha0=35., \
                deltamin=-90., deltastep=5.):

    """Wrapper to testsky - repeats the process for given dxarcsec,
dyarcsec, returning the rotation angle from the pointing test. Example call:

    unctytwod.wraptestsky(deltastep=5.)

    """

    # set up declination values
    deltas = np.arange(deltamin, 90.+deltastep, deltastep)
    thetas = np.zeros(deltas.size)

    for idelt in range(len(deltas)):
        thetas[idelt] = testsky(sidelen=sidelen, \
                                dxarcsec=dxarcsec, dyarcsec=dyarcsec, \
                                deltaback=True, \
                                returnwithposan=True, \
                                ncoarse=ncoarse, nfine=nfine, \
                                delta0=deltas[idelt])

    est = dxarcsec * np.sin(np.radians(deltas))
        
    # quick plot
    fig8 = plt.figure(8, figsize=(5,3))
    fig8.clf()
    ax8 = fig8.add_subplot(111)
    blah8a = ax8.scatter(deltas, thetas, c='#00274C', \
                         zorder=5, s=2, label=r'$\theta$')
    blah8b = ax8.plot(deltas, est, c='#9A3324', zorder=6, \
                      label=r'$\sin(\delta_0) \Delta \alpha_0$')
        
    ax8.set_xlabel(r'$\delta_0(^\circ)$')
    ax8.set_ylabel(r'$\theta$(")')
    ax8.set_xlim(-90., 90.)

    # show the parameters of this meta-run
    ssup = r'$(\Delta \alpha_0, \Delta\delta_0) = (%.1f, %.1f)$"' \
        % (dxarcsec, dyarcsec)

    ax8.set_title(r'%s, $\alpha_0=%.1f^\circ$' % (ssup, alpha0))
    
    leg8 = ax8.legend()
    
    fig8.subplots_adjust(bottom=0.2, left=0.2)

def testpattern(deg=2, kind='Polynomial', sidelen=1., ncoarse=41, \
                showbases=True, listpars=False, cmap='viridis', \
                norescale=False):

    """Test the psttern matrix construction. Example call:

    unctytwod.testpattern(2, kind='Polynomial', ncoarse=41, showbases=True)

    """

    # Generate points
    x, y = gridxieta(sidelen, ncoarse, ncoarse)

    # For timing
    t0 = time.time()
    
    PM = Patternmatrix(deg, x, y, kind=kind, norescale=norescale)

    # Now check that our convention matches what we expect by applying
    # this to a randomly generated parameter set
    pars = np.random.uniform(-.02, .02, PM.pattern.shape[-1])
    epsilon = np.matmul(PM.pattern, pars)

    W = np.zeros((x.size, 2, 2))
    W[:,0,0] = 1.
    W[:,1,1] = 1.

    # lhs
    WE = np.matmul(W, epsilon[:,:,np.newaxis]).squeeze()

    # Now for the transposed pattern matrix multiplied by this
    PT = np.transpose(PM.pattern, axes=(0,2,1) )
    lhs = np.matmul(PT, WE[:,:,np.newaxis]).squeeze()

    print("LHS shape:", lhs.shape)

    # now for the right hand side
    WP = np.matmul(W, PM.pattern)
    rhs = np.matmul(PT, WP)

    print("RHS shape:", rhs.shape)

    # now use the normal eqs
    beta = np.sum(lhs, axis=0)
    Hess = np.sum(rhs, axis=0)

    Hinv = np.linalg.inv(Hess)
    
    parsrecov = np.matmul(Hinv, beta)

    t1 = time.time()
    print("Time elapsed constructing and solving: %.2e sec" % (t1-t0))
    
    if listpars:
        for ipar in range(parsrecov.size):
            print("%.2e : %.2e" % (pars[ipar], parsrecov[ipar]))
    else:
        print("Generated:", pars)
        print("Recovered:", parsrecov)
            
    # Show the bases
    if showbases:
        print("testpattern INFO - plotting...")
        PM.showbases(cmap=cmap)

        # add a panel showing the transformed positions
        ilast = (PM.deg+1)**2
        thisfig = plt.figure(PM.fignum)
        ax = thisfig.add_subplot(PM.deg+1, PM.deg+1, ilast)
        dum = ax.scatter(epsilon[:,0], epsilon[:,1], s=1)

        print("testpattern INFO - ... done.")
