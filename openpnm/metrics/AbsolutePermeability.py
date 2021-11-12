from openpnm.utils import logging, Workspace, SettingsAttr
from openpnm.phases import GenericPhase
from openpnm.physics import GenericPhysics
from openpnm.algorithms import StokesFlow
from openpnm.metrics import GenericTransportMetrics
from openpnm import models
logger = logging.getLogger(__name__)
ws = Workspace()


class EffectiveDiffusivitySettings:
    prefix = 'perm'
    inlet = 'left'
    outlet = 'right'
    area = None
    length = None


class AbsolutePermeability(GenericTransportMetrics):
    r"""
    This class calculates the absolute permeability of the domain.

    """

    def __init__(self, settings={}, **kwargs):
        self.settings = SettingsAttr(EffectiveDiffusivitySettings, settings)
        super().__init__(settings=self.settings, **kwargs)

    def run(self):
        r"""
        Execute the diffusion simulations in the principle directions.

        """
        phase = GenericPhase(network=self.network)
        phase['pore.viscosity'] = 1.0
        phase['throat.viscosity'] = 1.0
        mod = models.physics.hydraulic_conductance.hagen_poiseuille
        for geom in self.project.geometries().values():
            phys = GenericPhysics(network=self.network,
                                  phase=phase, geometry=geom)
            phys.add_model(propname='throat.hydraulic_conductance', model=mod)
        inlet = self.network.pores(self.settings['inlet'])
        outlet = self.network.pores(self.settings['outlet'])
        perm = StokesFlow(network=self.project.network, phase=phase)
        perm.set_value_BC(pores=inlet, values=1)
        perm.set_value_BC(pores=outlet, values=0)
        perm.run()
        phase.update(perm.results())
        K = self._calc_eff_prop(inlets=inlet, outlets=outlet,
                                domain_area=self.settings['area'],
                                domain_length=self.settings['length'],
                                rates=perm.rate(pores=inlet),
                                prop_diff=1)
        return K
