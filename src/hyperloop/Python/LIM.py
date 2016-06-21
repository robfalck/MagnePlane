# Model for a Single Sided Linear Induction Motor(SLIM), using Circuit Model 
import math, numpy, scipy
from openmdao.core.component import Component
from openmdao.api import IndepVarComp, Component, Problem, Group, ScipyOptimizer, ExecComp, SqliteRecorder

"""Evaluates thrust generated by a single, single sided linear induction motor using the simplified circuit model.
	Inspired from the paper: DESIGN OF A SINGLE SIDED LINEAR INDUCTION MOTOR(SLIM) USING A USER INTERACTIVE COMPUTER PROGRAM"""
	

class Thrust(Component):
    def __init__(self):
	"""Establishes input parameters.All of input parameters can be obtained from experimental data. X_m was derived using a regression model 
	to conform the data from the Thrust Force vs Slip graph in the Coreless Linear Induction Motor (CLIM) paper published by NASA Armstrong.""" 
	
	"""This model also conforms to the order of amount of thrust given by propulsion_mechanics component.""" 
        super(Thrust, self).__init__()

        self.add_param('R2', val=.082, desc='resistance of rotor', units='ohms')
        self.add_param('R1', val = 7.6*10**-7, dest = 'per phase stator resistance', units = 'ohms')
        #self.add_param('p', val=1.0, desc = 'no. of poles', units = 'none') 
        self.add_param('P1', val = 180000, desc = 'input power', units = 'watts') 
        self.add_param('X_m', val=.9*10**-6, desc = 'per phase magnetic reactance', units = '' )
        self.add_param('m', val = 3.0, desc = 'input phase', units = 'none') 
        self.add_param('V1', val = 450.0, desc = 'input voltage', units = 'volts') 
        self.add_param('L_s', val = 0.6, desc = 'length of stator' , units = 'meters') 
        self.add_param('V_s', val = 16.31, desc = 'synchronous velocity', units = 'm/s')
        self.add_param('V_r', val = 15.5, desc = 'rotor velocity', units = 'm/s')        
        
        self.add_param('f', val = 60.0, desc ='input frequency', units = 'Hz')
        self.add_param('L', val = 0.0017, desc ='inductance of inductor', units = 'henries')
        self.add_param('c_time', val = 2.0, desc = 'contact time', units = 's')
        self.add_param('mass', val = 15000 , desc = 'mass of pod', units = 'kg')
        
        
        self.add_output('phi', 0.0, desc = 'phase angle', units = 'TBD')
        self.add_output('slip_ratio', 0.0, desc = 'slip ratio', units = 'TBD')
        self.add_output('reactance_of_inductor', 0.0, desc = 'reactance of inductor', units = 'TBD')
        self.add_output('omega', 0.0, desc = 'omega', units = 'TBD')
        self.add_output('thrust', 0.0, desc = 'thrust', units = 'N')
        self.add_output('a', 0.0, desc = 'acceleration', units = 'm/s^2')
        
    def solve_nonlinear(self, params, unknowns, resids):
	
	# Thrust eq : (P1^2*R2*X_m^2*S*(1-S)) / (m*V1^2*(cos(phi))^2*(R2^2+S^2*X_m**2))
	# Calls 4 additional sub-modules to calculate: 1) Phase angle(phi) 2) Slip Ratio(S) 3) Reactance of Stator(Inductor)(X_l) 4) Omega (w)
	
	#Parameters are initialized for simplification
        R1 = params['R1']
        R2 = params['R2'] 
        #p = params['p']
        P1 = params['P1']
        X_m = params['X_m']
        m = params['m']
        V1 = params['V1']
        L_s = params['L_s']
        V_s = params['V_s']
        V_r = params['V_r']
        
        f = params['f']
        L = params['L']
        
        mass = params['mass']
        c_time = params['c_time']
        
		#Sub-module phase_angle_calc is called to calculate phase angle(phi).
        unknowns['phi'] = self.phase_angle_calc(f, L, R1)
        phi = unknowns['phi']
        
        #Sub-module slip_ratio calculates slip ratio(S)
        unknowns['slip_ratio'] = self.slip_ratio(V_s, V_r)
        S = unknowns['slip_ratio']
        
        #Sub-module reactance_of_inductor is used to calculate stator(inductor) reactance.(X_l)
        unknowns['reactance_of_inductor'] = self.reactance_of_inductor(f,L)

        
        #Sub-module omega is used to calculate omega(w)
        unknowns['omega']= self.omega(f,L)

        
        unknowns['thrust'] = (P1**2*R2*X_m**2*S*(1-S)) / (m*V1**2*numpy.cos(phi)**2*(R2**2+S**2*X_m**2))
        unknowns['a'] = self.acceleration(P1, c_time, mass)





    
     
    def phase_angle_calc(self, f, L, R1):
        """Sub-module used to calculate phase angle using following eq. phi = arctan((2*pi*f*L) / R1)"""
        """ inputs are : 1) AC frequency - f 2) Inductance - L 3) Resistance of stator - R1"""
        phi = numpy.arctan((2*math.pi*f*L)/ R1 )
        return phi
    
    
    def slip_ratio(self, V_s, V_r):
        """Sub-module used to calculate slip ratio using following eq. slip = (V_s - V_r) / V_s"""
        """Inputs are: 1) Synchronous velocity - V_s 2) Rotor Velocity - V_r"""
        slip = (V_s - V_r) / V_s
        return slip
    
    def reactance_of_inductor(self, f, L):
        """Sub-module used to calculate reactance of inductor using following eq. slip = 2*pi*f*L"""
        """Inputs are: 1) frequency - f 2) Reactance of Inductor - L"""
        X_l = 2*math.pi*f*L
        return X_l
        
    def omega(self, f, L):
        """Sub-module used to calculate omega using following eq. omega = 2*pi*f*L"""
        """Inputs are: 1) frequency -f 2) Inductance - L"""
    
        w = 2*math.pi*f*L
        return w

    def acceleration(self,P1, c_time, mass ):
        """Sub-module used to calculate acceleration using following eq. acceleration = (P1 / (2*mass*c_time))^0.5 """
        """Inputs are: 1) Power Input -P1 2) mass - m  3)Contact time - c_time """
        a = (P1 / (2*mass*c_time))**0.5 
        return a
		
if __name__ == '__main__':
   
    #set up problem
    root = Group()
    p = Problem(root)
    p.root.add('comp', Thrust())
    p.setup()
    p.root.list_connections()
    p.run()
    
	#print following properties
    print 'phase angle : %f' %p['comp.omega']
    print 'slip ratio : %f' %p['comp.slip_ratio']
    print 'reactance of inductor : %f' %p['comp.reactance_of_inductor']
    print 'omega : %f' %p['comp.omega']
    print 'thrust : %f' %p['comp.thrust']
    print 'V1: %f' %p['comp.V1']

    #print 'acceleration : %f' %p['comp.a']
    