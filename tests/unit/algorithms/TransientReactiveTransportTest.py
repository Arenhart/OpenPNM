import pytest
import numpy as np
import openpnm as op
import numpy.testing as nt


class TransientImplicitReactiveTransportTest:

    def setup_class(self):
        np.random.seed(0)
        self.net = op.network.Cubic(shape=[3, 3, 1], spacing=1e-6)
        self.geo = op.geometry.GenericGeometry(network=self.net,
                                               pores=self.net.Ps,
                                               throats=self.net.Ts)
        self.geo['pore.volume'] = 1e-12
        self.phase = op.phases.GenericPhase(network=self.net)
        self.phys = op.physics.GenericPhysics(network=self.net,
                                              phase=self.phase,
                                              geometry=self.geo)
        self.phys['pore.A'] = -1e-13
        self.phys['pore.k'] = 2
        self.phys['throat.diffusive_conductance'] = 1e-12
        mod = op.models.physics.generic_source_term.standard_kinetics
        self.phys.add_model(propname='pore.reaction',
                            model=mod,
                            prefactor='pore.A',
                            exponent='pore.k',
                            X='pore.concentration',
                            regen_mode='deferred')
        self.settings = {'conductance': 'throat.diffusive_conductance',
                         'quantity': 'pore.concentration'}
        self.alg = op.algorithms.TransientReactiveTransport(network=self.net,
                                                            phase=self.phase,
                                                            settings=self.settings)
        self.alg.setup(quantity='pore.concentration',
                       conductance='throat.diffusive_conductance',
                       t_initial=0, t_final=1, t_step=0.1, t_tolerance=1e-7,
                       t_precision=10, rxn_tolerance=1e-6)
        self.alg.set_value_BC(pores=self.net.pores('back'), values=2)
        self.alg.set_source(propname='pore.reaction', pores=self.net.pores('front'))
        self.alg.set_IC(0)

    def test_transient_implicit_reactive_transport(self):
        self.alg.setup(t_scheme='implicit')
        self.alg.run()
        x = [2, 0.95029957, 0.41910096,
             2, 0.95029957, 0.41910096,
             2, 0.95029957, 0.41910096]
        y = self.alg["pore.concentration"]
        nt.assert_allclose(y, x, rtol=1e-5)

    def test_transient_cranknicolson_reactive_transport(self):
        self.alg.setup(t_scheme='cranknicolson')
        self.alg.run()
        x = [2, 0.94663043, 0.39438009,
             2, 0.94663043, 0.39438009,
             2, 0.94663043, 0.39438009]
        y = self.alg["pore.concentration"]
        # nt.assert_allclose(y, x, rtol=1e-5)

    def test_transient_reactive_transport_output_times(self):
        self.alg.setup(t_output=[0, 0.5, 0.7, 1])
        self.alg.run()
        times = ["pore.concentration@0",
                 "pore.concentration@5e-1",
                 "pore.concentration@7e-1",
                 "pore.concentration@1"]
        assert set(times).issubset(self.alg.keys())

    def test_transient_reactive_transport_results(self):
        times_total = ["pore.concentration@0",
                       "pore.concentration@5e-1",
                       "pore.concentration@7e-1",
                       "pore.concentration@1"]
        results_total = set(self.alg.results(steps=None).keys())
        results_total.discard("pore.concentration")
        assert set(times_total) == results_total
        times_partial = ["pore.concentration@5e-1",
                         "pore.concentration@1"]
        results_partial = set(self.alg.results(times=[0.5, 1]).keys())
        results_partial.discard("pore.concentration")
        assert set(times_partial) == results_partial

    def test_transient_steady_mode_reactive_transport(self):
        self.alg.setup(t_scheme="steady")
        self.alg.run()
        x = [2, 1.76556357, 1.53112766,
             2, 1.76556357, 1.53112766,
             2, 1.76556357, 1.53112766]
        y = self.alg["pore.concentration"]
        nt.assert_allclose(y, x, rtol=1e-5)
        self.alg.run()

    def test_consecutive_runs_preserves_solution(self):
        self.alg.setup(t_scheme='implicit')
        self.alg.run()
        x = [2, 0.95029957, 0.41910096,
             2, 0.95029957, 0.41910096,
             2, 0.95029957, 0.41910096]
        y = self.alg["pore.concentration"]
        nt.assert_allclose(y, x, rtol=1e-5)
        self.alg.run()
        y = self.alg["pore.concentration"]
        nt.assert_allclose(y, x, rtol=1e-5)

    def test_adding_bc_over_sources(self):
        with pytest.raises(Exception):
            self.alg.set_value_BC(pores=self.net.pores("right"), values=0.3)

    def test_adding_sources_over_bc(self):
        with pytest.raises(Exception):
            self.alg.set_source(propname='pore.reaction', pores=self.net.pores('left'))

    def test_set_IC_exception_if_quantity_not_specified(self):
        alg = op.algorithms.TransientReactiveTransport(network=self.net,
                                                       phase=self.phase)
        with pytest.raises(Exception):
            alg.set_IC(0)

    def test_IC_does_not_overwrite_value_BCs(self):
        alg = op.algorithms.TransientReactiveTransport(network=self.net,
                                                       phase=self.phase)
        alg.settings['quantity'] = 'pore.quantity'
        alg.set_value_BC(pores=[0, 1], values=1)
        alg.set_IC(0.5)
        x = [1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        y = alg['pore.ic']
        assert np.all(x == y)

    def test_value_BC_overwrites_ICs(self):
        alg = op.algorithms.TransientReactiveTransport(network=self.net,
                                                       phase=self.phase)
        alg.settings['quantity'] = 'pore.quantity'
        alg.set_IC(0.5)
        alg.set_value_BC(pores=[0, 1], values=1)
        x = [1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        y = alg['pore.ic']
        assert np.all(x == y)

    def teardown_class(self):
        ws = op.Workspace()
        ws.clear()


if __name__ == '__main__':

    t = TransientImplicitReactiveTransportTest()
    t.setup_class()
    self = t
    for item in t.__dir__():
        if item.startswith('test'):
            print('running test: '+item)
            t.__getattribute__(item)()
