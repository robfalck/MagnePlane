"""
Current Levitation Code
Outputs minimum mass and area of magnets needed for levitation at desired breakpoint velocity.
Outputs Halbach array wavelength, track resistance, and inductance can be used to find
drag force at any velocity using given pod weight.
"""
from math import pi, sin
from openmdao.api import Group, Component, IndepVarComp, Problem, ExecComp, ScipyOptimizer
import numpy as np

class BreakPointDrag(Component):
    """
    Current Break Point Drag Calculation very rough. Needs refinement.
    Default parameters taken from Inductrack I.
    Calculates minimum drag given at set breakpoint velocity desired with given track parameters.

    Params
    ------
    m_pod : float
        Mass of the hyperloop pod. Default value is 3000.
    b_res : float
        Residual strength of the Neodynium Magnets. Default value is 1.48.
    num_mag_hal : float
        Number of Magnets per Halbach Array. Default value is 4
    mag_thk : float
        Thickness of Magnet. Default value is 0.15.
    g : float
        Gravitational Acceleration. Default value is 9.81.
    l_pod : float
        Length of the Hyperloop pod. Default value is 22.
    gamma : float
        Percent factor used in Area. Default value is 1.
    w_track : float
        Width of track. Default value is 3.
    w_mag : float
        Width of magnet array. Default value is 3.
    spacing : float
        Halbach Spacing Factor. Default value is 0.0.
    w_strip : float
        Width of conductive strip. Default value is .005.
    num_sheets : float
        Number of laminated sheets. Default value is 1.0.
    delta_c : float
        Single layer thickness. Default value is .005.
    strip_c : float
        Center strip spacing. Default value is .0105.
    rc : float
        Electric resistance. Default value is 1.713*10**-8.
    MU0 : float
        Permeability of Free Space. Default value is 4*pi*10^-7.
    vel_b : float
        Breakpoint velocity of the pod. Default value is 23.
    h_lev : float
        Levitation height. Default value is .01.

    Returns
    -------
    lam : float
        Wavelength of the Halbach Array. Default value is 0.0.
    track_res : float
        Resistance of the track. Default value is 0.0
    track_ind : float
        Inductance of the track. Default value is 0.0.
    b0 : float
        Halbach Peak Strength. Default value is 0.0.
    mag_area : float
        Total area of the magnetic array. Default value is 0.0.
    omegab : float
        Breakpoint frequency of the induced current. Default value is 0.0.
    fyu : float
        Levitation force. Default value is 0.0.
    fxu : float
        Break point drag force. Default value is 0.0.
    ld_ratio : float
        Lift to drag ratio. Default value is 0.0.

    Notes
    -----
    [1] Friend, Paul. Magnetic Levitation Train Technology 1. Thesis.
    Bradley University, 2004. N.p.: n.p., n.d. Print.
    """

    def __init__(self):
        super(BreakPointDrag, self).__init__()

        # Pod Inputs
        self.add_param('m_pod', val=3000.0, units='kg', desc='Pod Mass')
        self.add_param('b_res',
                       val=1.48,
                       units='T',
                       desc='Residual Magnetic Flux')
        self.add_param('num_mag_hal',
                       val=4.0,
                       desc='Number of Magnets per Halbach Array')
        self.add_param('mag_thk', val=0.15, units='m', desc='Thickness of magnet')
        self.add_param('l_pod', val=22.0, units='m', desc='Length of Pod')
        self.add_param('gamma', val=1.0, desc='Percent Factor')
        self.add_param('w_mag', val=3.0, units='m', desc='Width of magnet array')
        self.add_param('spacing',
                       val=0.0,
                       units='m',
                       desc='Halbach Spacing Factor')

        # Track Inputs (laminated track)
        self.add_param('w_track', val=3.0, units='m', desc='Width of Track')
        self.add_param('w_strip',
                       val=0.005,
                       units='m',
                       desc='Width of Conductive Strip')
        self.add_param('num_sheets', val=1.0, desc='Number of Laminated Sheets')
        self.add_param('delta_c',
                       val=0.0005334,
                       units='m',
                       desc='Single Layer Thickness')
        self.add_param('strip_c',
                       val=0.0105,
                       units='m',
                       desc='Center Strip Spacing')
        self.add_param('rc',
                       val=1.713 * 10 ** -8,
                       units='ohm-m',
                       desc='Electric Resistivity')
        self.add_param('MU0',
                       val=4.0 * pi * 10 ** -7,
                       units='ohm*s/m',
                       desc='Permeability of Free Space')

        # Pod/Track Relation Inputs
        self.add_param('vel_b',
                       val=23.0,
                       units='m/s',
                       desc='Desired Breakpoint Velocity')
        self.add_param('h_lev', val=0.01, units='m', desc='Levitation Height')
        self.add_param('g', val=9.81, units='m/s**2', desc='Gravity')

        # Outputs
        self.add_output('lam', val=0.0, units='m', desc='Halbach wavelength')
        self.add_output('track_ind', val=0.0, units='ohm*s', desc='Inductance')
        self.add_output('b0', val=0.0, units='T', desc='Halbach peak strength')
        self.add_output('mag_area',
                        val=0.0,
                        units='m**2',
                        desc='Total Area of Magnets')
        self.add_output('omegab',
                        val=0.0,
                        units='rad/s',
                        desc='Breakpoint Frequency')
        self.add_output('fyu', val=0.0, units='N', desc='Levitation Force')
        self.add_output('fxu', val=0.0, units='N', desc='Break Point Drag Force')
        self.add_output('ld_ratio', val=0.0, desc='Lift to Drag Ratio')
        self.add_output('track_res', val=0.0, units='ohm', desc='Resistance')

    def solve_nonlinear(self, params, unknowns, resids):

        # Pod Parameters
        vel_b = params['vel_b']  # Breakpoint Velocity
        b_res = params['b_res']  # Magnet Strength
        num_mag_hal = params['num_mag_hal']  # Number of Magnets per Wavelength
        h_lev = params['h_lev']  # Desired Levitation Height
        mag_thk = params['mag_thk']  # Magnet Thickness
        gamma = params['gamma']  # Area Scalar
        l_pod = params['l_pod']  # Length of the Pod
        w_mag = params['w_mag']  # Width of Magnetic Array
        spacing = params['spacing']

        # Track Parameters
        w_track = params['w_track']  # Width of Track
        w_strip = params['w_strip']  # Width of Conductive Strip
        num_sheets = params['num_sheets']  # Number of Laminated Layers
        delta_c = params['delta_c']  # Single Layer Thickness
        strip_c = params['strip_c']  # Center Strip Spacing
        rc = params['rc']  # Electrical Resistivity of Material
        MU0 = params['MU0']  # Permeability of Free Space

        # Compute Intermediate Variables
        track_res = rc * w_track / (delta_c * w_strip * num_sheets)  # Track Resistance

        lam = num_mag_hal * mag_thk + spacing  # Compute Wavelength
        b0 = b_res * (1. - np.exp(-2. * pi * mag_thk / lam)) * (
            (sin(pi / num_mag_hal)) / (pi / num_mag_hal))  # Compute Peak Field Strength
        track_ind = MU0 * w_track / (4 * pi * strip_c / lam)  # Compute Track Inductance
        mag_area = w_mag * l_pod * gamma  # Compute Magnet Area

        if vel_b == 0:
            omegab = 0
            fyu = 0
            fxu = 0
            ld_ratio = 0
        else:
            omegab = 2 * pi * vel_b / lam  # Compute Induced Frequency
            fyu = (b0**2. * w_mag / (4. * pi * track_ind * strip_c / lam)) * (1. / (
                1. + (track_res / (omegab * track_ind))**2)) * np.exp(
                    -4. * pi * h_lev / lam) * mag_area  # Compute Lift Force
            fxu = (b0**2. * w_mag / (4. * pi * track_ind * strip_c / lam)) * (
                (track_res / (omegab * track_ind)) / (1. + (track_res / (omegab * track_ind))**2.)) * np.exp(
                    -4 * pi * h_lev / lam) * mag_area  # Compute Break Point Drag Force
            ld_ratio = fyu / fxu  # Compute Lift to Drag Ratio

        unknowns['lam'] = lam
        unknowns['b0'] = b0
        unknowns['track_ind'] = track_ind
        unknowns['mag_area'] = mag_area
        unknowns['omegab'] = omegab
        unknowns['fyu'] = fyu
        unknowns['fxu'] = fxu
        unknowns['ld_ratio'] = ld_ratio
        unknowns['track_res'] = track_res

    # def linearize(self, params, unknowns, resids):
    #
    #     # Define Parameters
    #
    #     J = {}
    #     J['fxu','mag_thk'] =
    #     J['fxu', 'gamma'] =
    #
    #     return J


class MagMass(Component):
    """
    Current Magnet Mass Calculation very rough. Needs refinement.
    Default parameters taken from Inductrack I.
    Calculates minimum magnet mass needed at set breakpoint velocity desired with given track parameters.

    Params
    ------
    mag_thk : float
        Thickness of Magnet. Default value is 0.15.
    rho_mag : float
        Density of Magnet. Default value is 7500.
    l_pod : float
        Length of the Hyperloop pod. Default value is 22.
    gamma : float
        Percent factor used in Area. Default value is 1.
    w_mag : float
        Width of magnet array. Default value is 3.
    cost_per_kg : flost
        Cost of the magnets per kilogram. Default value is 44.

    Returns
    -------
    mag_area : float
        Total area of the magnetic array. Default value is 0.0
    m_mag : float
        Mass of the permanent magnets. Default value is 0.0.
    cost : float
        Total cost of the magnets. Default value is 0.0.

    Notes
    -----
    [1] Friend, Paul. Magnetic Levitation Train Technology 1. Thesis.
    Bradley University, 2004. N.p.: n.p., n.d. Print.
    """

    def __init__(self):
        super(MagMass, self).__init__()

        # Pod Inputs
        self.add_param('mag_thk', val=0.15, units='m', desc='Thickness of Magnet')
        self.add_param('rho_mag',
                       val=7500.0,
                       units='kg/m**3',
                       desc='Density of Magnet')
        self.add_param('l_pod', val=22.0, units='m', desc='Length of Pod')
        self.add_param('gamma', val=1.0, desc='Percent Factor')
        self.add_param('cost_per_kg',
                       val=44.0,
                       units='USD/kg',
                       desc='Cost of Magnet per Kilogram')
        self.add_param('w_mag', val=3.0, units='m', desc='Width of Magnet Array')

        # Outputs
        self.add_output('mag_area', val=0.0, units='m', desc='Total Area of Magnets')
        self.add_output('m_mag', val=0.0, units='kg', desc='Mass of Magnets')
        self.add_output('cost', val=0.0, units='USD', desc='Cost of Magnets')

    def solve_nonlinear(self, params, unknowns,
                        resids):  # params, unknowns, residuals

        # Parameters
        mag_thk = params['mag_thk']  # Thickness of Magnet
        w_mag = params['w_mag']  # Width of Magnet Array
        gamma = params['gamma']  # Area Scalar
        l_pod = params['l_pod']  # Length of Pod
        rho_mag = params['rho_mag']  # Density of Magnets
        cost_per_kg = params['cost_per_kg']  # Cost per kg of Magnet

        # Compute Intermediate Variables
        mag_area = w_mag * l_pod * gamma  # Compute Magnet Area
        m_mag = rho_mag * mag_area * mag_thk  # Compute Magnet Mass
        cost = m_mag * cost_per_kg  # Compute Total Magnet Cost

        unknowns['mag_area'] = mag_area
        unknowns['m_mag'] = m_mag
        unknowns['cost'] = cost

    # def linearize(self, params, unknowns, resids):
    #
    #     # Define Parameters
    #     rho_mag = params['rho_mag']
    #     w_track = params['w_track']
    #     l_pod = params['l_pod']
    #     mag_thk = params['mag_thk']
    #
    #
    #     J = {}
    #     J['m_mag', 'mag_thk'] = rho_mag*mag_thk
    #     J['m_mag', 'gamma'] = rho_mag*w_track*l_pod*mag_thk
    #
    #     return J


if __name__ == "__main__":

    top = Problem()
    root = top.root = Group()

    # Define Parameters
    params = (('mag_thk', .05, {'units': 'm'}), ('gamma', .05),
              ('m_pod', 3000.0, {'units': 'kg'}),
              ('g', 9.81, {'units': 'm/s**2'}))

    # Add Components
    root.add('input_vars', IndepVarComp(params))
    root.add('p', BreakPointDrag())
    root.add('q', MagMass())

    # Constraint Equation
    root.add('con1', ExecComp('c1 = (fyu - m_pod * g)/1e5'))

    # Connect
    root.connect('input_vars.m_pod', 'p.m_pod')
    root.connect('p.m_pod', 'con1.m_pod')
    root.connect('p.fyu', 'con1.fyu')
    root.connect('input_vars.g', 'p.g')
    root.connect('p.g', 'con1.g')

    root.connect('input_vars.mag_thk', 'p.mag_thk')
    root.connect('input_vars.mag_thk', 'q.mag_thk')

    root.connect('input_vars.gamma', 'p.gamma')
    root.connect('input_vars.gamma', 'q.gamma')

    # Finite Difference
    root.deriv_options['type'] = 'fd'
    root.fd_options['form'] = 'forward'
    root.fd_options['step_size'] = 1.0e-6

    # Optimizer Driver
    top.driver = ScipyOptimizer()
    top.driver.options['optimizer'] = 'COBYLA'

    # Design Variables
    top.driver.add_desvar('input_vars.mag_thk', lower=.01, upper=.15, scaler=100)
    top.driver.add_desvar('input_vars.gamma', lower=0.1, upper=1.0)

    # Add Constraint
    top.driver.add_constraint('con1.c1', lower=0.0)

    # Problem Objective
    alpha = .5
    root.add('obj_cmp', ExecComp('obj = (alpha*fxu)/1000 + ((1-alpha)*m_mag)'))
    root.connect('p.fxu', 'obj_cmp.fxu')
    root.connect('q.m_mag', 'obj_cmp.m_mag')

    top.driver.add_objective('obj_cmp.obj')

    top.setup()

    top.run()

    # from openmdao.devtools.partition_tree_n2 import view_tree
    # view_tree(top)

    # Print Outputs for Debugging
    # print('\n')
    # print('Lift to BreakPointDrag Ratio is %f' % top['p.ld_ratio'])
    # print('fyu is %f' % top['p.fyu'])
    # print('fxu is %f' % top['p.fxu'])
    # print('c1 is %f' % top['con1.c1'])
    # print('Total Magnet Area is %f m^2' % top['p.mag_area'])
    # print('Total Magnet Weight is %f kg' % top['q.m_mag'])
    # print('Total Magnet Cost is $%f' % top['q.cost'])
    # print('mag_thk is %f m' % top['p.mag_thk'])
    # print('Gamma is %f' % top['p.gamma'])
    # print('\n')
    # print('track_res is %f m' % top['p.track_res'])
    # print('track_ind is %12.12f m' % top['p.track_ind'])
    # print('b0 is %f m' % top['p.b0'])
