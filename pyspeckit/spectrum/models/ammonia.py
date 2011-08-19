"""
Ammonia inversion transition TKIN fitter translated from Erik Rosolowsky's
http://svn.ok.ubc.ca/svn/signals/nh3fit/
"""
import numpy as np
from mpfit import mpfit
from .. import units
from . import fitter
import matplotlib.cbook as mpcb
import copy

line_names = ['oneone','twotwo','threethree','fourfour']

freq_dict = { 
    'oneone':     23.694506e9,
    'twotwo':     23.722633335e9,
    'threethree': 23.8701296e9,
    'fourfour':   24.1394169e9,
    }
aval_dict = {
    'oneone':     1.712e-7,  #64*!pi**4/(3*h*c**3)*nu11**3*mu0**2*(1/2.)
    'twotwo':     2.291e-7,  #64*!pi**4/(3*h*c**3)*nu22**3*mu0**2*(2/3.)
    'threethree': 2.625e-7,  #64*!pi**4/(3*h*c**3)*nu33**3*mu0**2*(3/4.)
    'fourfour':   3.167e-7,  #64*!pi**4/(3*h*c**3)*nu44**3*mu0**2*(4/5.)
    }
ortho_dict = {
    'oneone':     False,
    'twotwo':     False,
    'threethree': True,
    'fourfour':   False,
    }
n_ortho = np.arange(0,28,3) # 0..3..27
n_para = np.array([x for x in range(28) if x % 3 != 0])

voff_lines_dict = {
    'oneone': [19.8513, 19.3159, 7.88669, 7.46967, 7.35132, 0.460409, 0.322042,
        -0.0751680, -0.213003, 0.311034, 0.192266, -0.132382, -0.250923, -7.23349,
        -7.37280, -7.81526, -19.4117, -19.5500],
    'twotwo':[26.5263, 26.0111, 25.9505, 16.3917, 16.3793, 15.8642, 0.562503,
        0.528408, 0.523745, 0.0132820, -0.00379100, -0.0132820, -0.501831,
        -0.531340, -0.589080, -15.8547, -16.3698, -16.3822, -25.9505, -26.0111,
        -26.5263],
    'threethree':[29.195098, 29.044147, 28.941877, 28.911408, 21.234827,
        21.214619, 21.136387, 21.087456, 1.005122, 0.806082, 0.778062,
        0.628569, 0.016754, -0.005589, -0.013401, -0.639734, -0.744554,
        -1.031924, -21.125222, -21.203441, -21.223649, -21.076291, -28.908067,
        -28.938523, -29.040794, -29.191744],
    'fourfour':[  0.        , -30.49783692,  30.49783692,   0., 24.25907811,
        -24.25907811,   0.        ]
                      }

tau_wts_dict = {
    'oneone': [0.0740740, 0.148148, 0.0925930, 0.166667, 0.0185190, 0.0370370,
        0.0185190, 0.0185190, 0.0925930, 0.0333330, 0.300000, 0.466667,
        0.0333330, 0.0925930, 0.0185190, 0.166667, 0.0740740, 0.148148],
    'twotwo': [0.00418600, 0.0376740, 0.0209300, 0.0372090, 0.0260470,
        0.00186000, 0.0209300, 0.0116280, 0.0106310, 0.267442, 0.499668,
        0.146512, 0.0116280, 0.0106310, 0.0209300, 0.00186000, 0.0260470,
        0.0372090, 0.0209300, 0.0376740, 0.00418600],
    'threethree': [0.012263, 0.008409, 0.003434, 0.005494, 0.006652, 0.008852,
        0.004967, 0.011589, 0.019228, 0.010387, 0.010820, 0.009482, 0.293302,
        0.459109, 0.177372, 0.009482, 0.010820, 0.019228, 0.004967, 0.008852,
        0.006652, 0.011589, 0.005494, 0.003434, 0.008409, 0.012263],
    'fourfour': [0.2431, 0.0162, 0.0162, 0.3008, 0.0163, 0.0163, 0.3911]}

def ammonia(xarr, tkin=20, tex=None, ntot=1e14, width=1,
        xoff_v=0.0, fortho=1.0, tau11=None, fillingfraction=None, return_tau=False,
        thin=False, verbose=False ):
    """
    Generate a model Ammonia spectrum based on input temperatures, column, and
    gaussian parameters

    ntot can be specified as a column density (e.g., 10^15) or a log-column-density (e.g., 15)
    tex can be specified or can be assumed LTE if unspecified, if tex>tkin, or if "thin"
        is specified
    "thin" uses a different parametetrization and requires only the optical depth, width, offset,
        and tkin to be specified
    If tau11 is specified, ntot is NOT fit but is set to a fixed value
    fillingfraction is an arbitrary scaling factor to apply to the model
    fortho is the ortho/(ortho+para) fraction.  The default is to assume all ortho.
    xoff_v is the velocity offset in km/s 

    (not implemented) if tau11 is specified, ntot is ignored
    """

    # Convert X-units to frequency in GHz
    xarr = copy.copy(xarr)
    xarr.convert_to_unit('GHz', quiet=True)

    # Convert X-units to frequency in GHz
    # OLD VERSION if xunits in units.frequency_dict:
    # OLD VERSION     xarr = np.copy(xarr) * units.frequency_dict[xunits] / units.frequency_dict['GHz']
    # OLD VERSION elif xunits in units.velocity_dict:
    # OLD VERSION     if line in freq_dict:
    # OLD VERSION         xarr = (freq_dict[line] - (np.copy(xarr) * 
    # OLD VERSION                 (units.velocity_dict[xunits] / units.velocity_dict['m/s'] / units.speedoflight_ms) *
    # OLD VERSION                 freq_dict[line]) ) / units.frequency_dict['GHz']
    # OLD VERSION     else:
    # OLD VERSION         raise Exception("Xunits is velocity-type (%s) but line %s is not in the list." % (xunits,line))
    # OLD VERSION else:
    # OLD VERSION     raise Exception("xunits not recognized: %s" % (xunits))

    if tex is not None:
        if tex > tkin: # cannot have Tex > Tkin
            tex = tkin 
        elif thin: # tex is not used in this case
            tex = tkin
    else:
        tex = tkin

    if thin:
        ntot = 1e15
    elif 5 < ntot < 25: 
        # allow ntot to be specified as a logarithm.  This is
        # safe because ntot < 1e10 gives a spectrum of all zeros, and the
        # plausible range of columns is not outside the specified range
        ntot = 10**ntot

    # fillingfraction is an arbitrary scaling for the data
    # The model will be (normal model) * fillingfraction
    if fillingfraction is None:
        fillingfraction = 1.0

    ckms = 2.99792458e5
    ccms = ckms*1e5
    g1 = 1                
    g2 = 1                
    h = 6.6260693e-27     
    kb = 1.3806505e-16     
    mu0 = 1.476e-18               # Dipole Moment in cgs (1.476 Debeye)
  
    # Generate Partition Functions  
    nlevs = 51
    jv=np.arange(nlevs)
    ortho = jv % 3 == 0
    para = True-ortho
    Jpara = jv[para]
    Jortho = jv[ortho]
    Brot = 298117.06e6
    Crot = 186726.36e6
    Zpara = (2*Jpara+1)*np.exp(-h*(Brot*Jpara*(Jpara+1)+
        (Crot-Brot)*Jpara**2)/(kb*tkin))
    Zortho = 2*(2*Jortho+1)*np.exp(-h*(Brot*Jortho*(Jortho+1)+
        (Crot-Brot)*Jortho**2)/(kb*tkin))

    runspec = np.zeros(len(xarr))
    
    tau_dict = {}
    para_count = 0
    ortho_count = 1 # ignore 0-0

    if tau11 is not None and thin:
        dT0 = 41.5                    # Energy diff between (2,2) and (1,1) in K
        trot = tkin/(1+tkin/dT0*np.log(1+0.6*np.exp(-15.7/tkin)))
        tau_dict['oneone']     = tau11
        tau_dict['twotwo']     = tau11*(23.722/23.694)**2*4/3.*5/3.*np.exp(-41.5/trot)
        tau_dict['threethree'] = tau11*(23.8701279/23.694)**2*3/2.*14./3.*np.exp(-101.1/trot)
        tau_dict['fourfour']   = tau11*(24.1394169/23.694)**2*8/5.*9/3.*np.exp(-177.34/trot)
    else:
        for linename in line_names:
            if ortho_dict[linename]:
                orthoparafrac = fortho
                Z = Zortho 
                count = ortho_count
                ortho_count += 1
            else:
                orthoparafrac = 1.0-fortho
                Z = Zpara
                count = para_count # need to treat partition function separately
                para_count += 1
            tau_dict[linename] = (ntot * orthoparafrac * Z[count]/(Z.sum()) / ( 1
                + np.exp(-h*freq_dict[linename]/(kb*tkin) )) * ccms**2 /
                (8*np.pi*freq_dict[linename]**2) * aval_dict[linename]*
                (1-np.exp(-h*freq_dict[linename]/(kb*tex))) /
                (width/ckms*freq_dict[linename]*np.sqrt(2*np.pi)) )

    # allow tau11 to be specified instead of ntot
    # in the thin case, this is not needed: ntot plays no role
    if tau11 is not None and not thin:
        tau11_temp = tau_dict['oneone']
        # re-scale all optical depths so that tau11 is as specified, but the relative taus
        # match theory
        for linename,tau in tau_dict.iteritems():
            tau_dict[linename] = tau * tau11/tau11_temp

    for linename in line_names:
        voff_lines = np.array(voff_lines_dict[linename])
        tau_wts = np.array(tau_wts_dict[linename])
  
        lines = (1-voff_lines/ckms)*freq_dict[linename]/1e9
        tau_wts = tau_wts / (tau_wts).sum()
        nuwidth = np.abs(width/ckms*lines)
        nuoff = xoff_v/ckms*lines
  
        # tau array
        tauprof = np.zeros(len(xarr))
        for kk,no in enumerate(nuoff):
            tauprof += (tau_dict[linename] * tau_wts[kk] *
                    np.exp(-(xarr+no-lines[kk])**2 / (2.0*nuwidth[kk]**2)) *
                    fillingfraction)
  
        T0 = (h*xarr*1e9/kb) # "temperature" of wavelength
        if tau11 is not None and thin:
            runspec = tauprof+runspec
        else:
            runspec = (T0/(np.exp(T0/tex)-1)-T0/(np.exp(T0/2.73)-1))*(1-np.exp(-tauprof))+runspec
        if runspec.min() < 0:
            raise ValueError("Model dropped below zero.  That is not possible normally.")

    if verbose:
        print "tkin: %g  tex: %g  ntot: %g  width: %g  xoff_v: %g  fortho: %g  fillingfraction: %g" % (tkin,tex,ntot,width,xoff_v,fortho,fillingfraction)

    if return_tau:
        return tau_dict
  
    return runspec

class ammonia_model(fitter.SimpleFitter):

    def __init__(self,npeaks=1,npars=6,multisingle='multi'):
        self.npeaks = npeaks
        self.npars = npars

        self.onepeakammonia = fitter.vheightmodel(ammonia)
        #self.onepeakammoniafit = self._fourparfitter(self.onepeakammonia)

        if multisingle in ('multi','single'):
            self.multisingle = multisingle
        else:
            raise Exception("multisingle must be multi or single")

    def __call__(self,*args,**kwargs):
        if self.multisingle == 'single':
            return self.onepeakammoniafit(*args,**kwargs)
        elif self.multisingle == 'multi':
            return self.multinh3fit(*args,**kwargs)

    def n_ammonia(self, pars=None, parnames=None, **kwargs):
        """
        Returns a function that sums over N ammonia line profiles, where N is the length of
        tkin,tex,ntot,width,xoff_v,fortho *OR* N = len(pars) / 6

        The background "height" is assumed to be zero (you must "baseline" your
        spectrum before fitting)

        pars  - a list with len(pars) = 6n, assuming tkin,tex,ntot,width,xoff_v,fortho repeated
        """
        if len(pars) != len(parnames):
            raise ValueError("Wrong array lengths!")

        def L(x):
            v = np.zeros(len(x))
            for jj in xrange(self.npeaks):
                modelkwargs = kwargs.copy()
                for ii in xrange(len(pars)/self.npeaks):
                    modelkwargs.update({parnames[ii+jj].strip('0123456789'):pars[ii+jj]})
                v += ammonia(x,**modelkwargs)
            return v
        return L

    def multinh3fit(self, xax, data, npeaks=1, err=None, 
            params=[20,20,14,1.0,0.0,0.5],
            parnames=['tkin','tex','ntot','width','xoff_v','fortho'],
            fixed=[False,False,False,False,False,False],
            limitedmin=[True,True,True,True,False,True],
            limitedmax=[False,False,False,False,False,True], minpars=[2.73,2.73,0,0,0,0],
            maxpars=[0,0,0,0,0,1], quiet=True, shh=True, veryverbose=False, **kwargs):
        """
        Fit multiple nh3 profiles

        Inputs:
           xax - x axis
           data - y axis
           npeaks - How many nh3 profiles to fit?  Default 1 (this could supersede onedgaussfit)
           err - error corresponding to data

         These parameters need to have length = 6*npeaks.  If npeaks > 1 and length = 6, they will
         be replicated npeaks times, otherwise they will be reset to defaults:
           params - Fit parameters: [tkin, tex, ntot (or tau), width, offset, ortho fraction] * npeaks
                  If len(params) % 6 == 0, npeaks will be set to len(params) / 6
           fixed - Is parameter fixed?
           limitedmin/minpars - set lower limits on each parameter (default: width>0, Tex and Tkin > Tcmb)
           limitedmax/maxpars - set upper limits on each parameter

           quiet - should MPFIT output each iteration?
           shh - output final parameters?

        Returns:
           Fit parameters
           Model
           Fit errors
           chi2
        """

        self.npars = len(params) / npeaks

        if len(params) != npeaks and (len(params) / self.npars) > npeaks:
            npeaks = len(params) / self.npars 
        self.npeaks = npeaks

        if isinstance(params,np.ndarray): params=params.tolist()

        # make sure all various things are the right length; if they're not, fix them using the defaults
        for parlist in (params,parnames,fixed,limitedmin,limitedmax,minpars,maxpars):
            if len(parlist) != self.npars*self.npeaks:
                # if you leave the defaults, or enter something that can be multiplied by npars to get to the
                # right number of gaussians, it will just replicate
                if len(parlist) == self.npars: 
                    parlist *= npeaks 
                elif parlist==params: # this instance shouldn't really be possible
                    parlist[:] = [20,20,1e10,1.0,0.0,0.5] * npeaks
                elif parlist==fixed:
                    parlist[:] = [False] * len(params)
                elif parlist==limitedmax: # only fortho, fillingfraction have upper limits
                    parlist[:] = (np.array(parnames) == 'fortho') + (np.array(parnames) == 'fillingfraction')
                elif parlist==limitedmin: # no physical values can be negative except velocity
                    parlist[:] = (np.array(parnames) != 'xoff_v')
                elif parlist==minpars: # all have minima of zero except kinetic temperature, which can't be below CMB.  Excitation temperature technically can be, but not in this model
                    parlist[:] = ((np.array(parnames) == 'tkin') + (np.array(parnames) == 'tex')) * 2.73
                elif parlist==maxpars: # fractions have upper limits of 1.0
                    parlist[:] = ((np.array(parnames) == 'fortho') + (np.array(parnames) == 'fillingfraction')).astype('float')
                elif parlist==parnames: # assumes the right number of parnames (essential)
                    parlist[:] = list(parnames) * self.npeaks 

        parinfo = [ {'n':ii, 'value':params[ii],
            'limits':[minpars[ii],maxpars[ii]],
            'limited':[limitedmin[ii],limitedmax[ii]], 'fixed':fixed[ii],
            'parname':parnames[ii]+str(ii/self.npars),
            'mpmaxstep':float(parnames[ii] in ('tex','tkin')), # must force small steps in temperature (True = 1.0)
            'error': 0} 
            for ii in xrange(len(params)) ]

        def mpfitfun(x,y,err):
            if err is None:
                def f(p,fjac=None): return [0,(y-self.n_ammonia(pars=p, parnames=[pi['parname'] for pi in parinfo], **kwargs)(x))]
            else:
                def f(p,fjac=None): return [0,(y-self.n_ammonia(pars=p, parnames=[pi['parname'] for pi in parinfo], **kwargs)(x))/err]
            return f

        if veryverbose:
            print "GUESSES: "
            print "\n".join(["%s: %s" % (p['parname'],p['value']) for p in parinfo])

        mp = mpfit(mpfitfun(xax,data,err),parinfo=parinfo,quiet=quiet)
        mpp = mp.params
        if mp.perror is not None: mpperr = mp.perror
        else: mpperr = mpp*0
        chi2 = mp.fnorm

        if mp.status == 0:
            raise Exception(mp.errmsg)

        for i,p in enumerate(mpp):
            parinfo[i]['value'] = p
            parinfo[i]['error'] = mpperr[i]

        if not shh:
            print "Fit message: ",mp.errmsg
            print "Final fit values: "
            for i,p in enumerate(mpp):
                print parinfo[i]['parname'],p," +/- ",mpperr[i]
            print "Chi2: ",mp.fnorm," Reduced Chi2: ",mp.fnorm/len(data)," DOF:",len(data)-len(mpp)

        if mpp[1] > mpp[0]: mpp[1] = mpp[0]  # force Tex>Tkin to Tex=Tkin (already done in n_ammonia)
        self.mp = mp
        self.mpp = mpp
        self.mpperr = mpperr
        self.model = self.n_ammonia(pars=mpp, parnames=parnames, **kwargs)(xax)
        indiv_parinfo = [parinfo[jj*self.npars:(jj+1)*self.npars] for jj in xrange(len(parinfo)/self.npars)]
        modelkwargs = [
                dict([(p['parname'].strip("0123456789").lower(),p['value']) for p in pi])
                for pi in indiv_parinfo]
        self.tau_list = [ammonia(xax,return_tau=True,**mk) for mk in modelkwargs]
        self.parinfo = parinfo
        return mpp,self.model,mpperr,chi2

    def moments(self, Xax, data, negamp=None, veryverbose=False,  **kwargs):
        """
        Returns a very simple and likely incorrect guess
        """

        # TKIN, TEX, ntot, width, center, ortho fraction
        return [20,10, 1e15, 1.0, 0.0, 1.0]

    def annotations(self):
        tex_key = {'tkin':'T_K','tex':'T_{ex}','ntot':'N','fortho':'F_o','width':'\\sigma','xoff_v':'v','fillingfraction':'FF','tau11':'\\tau_{1-1}'}
        label_list = [ "$%s(%i)$=%6.4g $\\pm$ %6.4g" % (tex_key[pinfo['parname'].strip("0123456789")],int(pinfo['parname'][-1]),pinfo['value'],pinfo['error']) for pinfo in self.parinfo]
        labels = tuple(mpcb.flatten(label_list))
        return labels
