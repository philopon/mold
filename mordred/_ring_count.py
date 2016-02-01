import networkx

from rdkit import Chem

from ._base import Descriptor


class RingCountBase(Descriptor):
    explicit_hydrogens = False

    def __reduce_ex__(self, version):
        return self.__class__, ()


class Rings(RingCountBase):
    __slots__ = ()

    def calculate(self, mol):
        return [frozenset(s) for s in Chem.GetSymmSSSR(mol)]


class FusedRings(RingCountBase):
    __slots__ = ()

    def dependencies(self):
        return dict(Rings=Rings())

    def calculate(self, mol, Rings):
        if len(Rings) < 2:
            return []

        G = networkx.Graph()

        l = len(Rings)
        for i, j in ((i, j) for i in range(l) for j in range(i + 1, l)):
            if len(Rings[i] & Rings[j]) >= 2:
                G.add_edge(i, j)

        return [
            frozenset(j for i in ring_ids for j in Rings[i])
            for ring_ids in networkx.connected_components(G)
        ]


class RingCount(RingCountBase):
    r"""ring count descriptor.

    :type order: int or None
    :param order: number of bonds in ring

    :type greater: bool
    :param greater: count length or greater rings

    :type fused: bool
    :param fused: count fused rings

    :type aromatic: bool or None
    :param aromatic:
        * True: count aromatic rings
        * False: count non-aromatic rings
        * None: count any rings

    :type hetero: bool or None
    :param hetero:
        * True: count hetero rings
        * False: count carbon rings
        * None: count any rings
    """

    @classmethod
    def preset(cls):
        for fused in [False, True]:
            for arom in [None, True, False]:
                for hetero in [None, True]:
                    yield cls(None, False, fused, arom, hetero)
                    for n in range(4 if fused else 3, 13):
                        yield cls(n, False, fused, arom, hetero)

                    yield cls(12, True, fused, arom, hetero)

    def __str__(self):
        attrs = []

        if self._greater:
            attrs.append('G')

        if self._order is not None:
            attrs.append(str(self._order))

        if self._fused:
            attrs.append('F')

        if self._aromatic is True:
            attrs.append('a')
        elif self._aromatic is False:
            attrs.append('A')

        if self._hetero is True:
            attrs.append('H')
        elif self._hetero is False:
            attrs.append('C')

        return 'n{}Ring'.format(''.join(attrs))

    __slots__ = ('_order', '_greater', '_fused', '_aromatic', '_hetero',)

    def __reduce_ex__(self, version):
        return (
            self.__class__,
            (self._order, self._greater, self._fused, self._aromatic, self._hetero)
        )

    def __init__(self, order=None, greater=False, fused=False, aromatic=None, hetero=None):
        self._order = order
        self._greater = greater
        self._fused = fused
        self._aromatic = aromatic
        self._hetero = hetero

    def dependencies(self):
        return dict(
            Rs=(FusedRings if self._fused else Rings)()
        )

    def _check_order(self, R):
        if self._order is None:
            return True

        if self._greater:
            return len(R) >= self._order
        else:
            return len(R) == self._order

    def _check_arom(self, mol, R):
        if self._aromatic is None:
            return True

        is_arom = all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in R)

        if self._aromatic:
            return is_arom

        return not is_arom

    def _check_hetero(self, mol, R):
        if self._hetero is None:
            return True

        has_hetero = any(mol.GetAtomWithIdx(i).GetAtomicNum() != 6 for i in R)

        if self._hetero:
            return has_hetero

        return not has_hetero

    def calculate(self, mol, Rs):
        return sum(
            1 for R in Rs
            if self._check_order(R) and self._check_arom(mol, R) and self._check_hetero(mol, R)
        )

    rtype = int