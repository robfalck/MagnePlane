import numpy as np
from openmdao.api import Group, Problem
from hyperloop.Python.pod.pod_mass import PodMass

def create_problem(component):
    root = Group()
    prob = Problem(root)
    prob.root.add('comp', component)
    return prob

class Test1(object):
    def test_case1(self):

        component = PodMass()
        prob = create_problem(component)

        prob.setup()

        prob['comp.mag_mass'] = 1.0
        prob['comp.podgeo_d'] = 1.0
        prob['comp.al_rho'] = 2800.00
        prob['comp.motor_mass'] = 1.0
        prob['comp.battery_mass'] = 1.0
        prob['comp.comp_mass'] = 1.0
        prob['comp.pod_len'] = 1.0
        prob.run()

        assert np.isclose(prob['comp.pod_mass'], 10479.95, rtol = 1.)



