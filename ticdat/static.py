"""
Provides assistance for hard coded ticDat objects.
"""

import ticdat._private.utils as _utls
from ticdat._private.utils import verify, freezableFactory, FrozenDict, doIt

class _TicDat(_utls.freezableFactory(object, "_isFrozen")) :
    def _freeze(self):
        if getattr(self, "_isFrozen", False) :
            return
        for t in getattr(self, "_tables", {}) :
            for v in getattr(self, t).values() :
                v._dataFrozen =True
                v._attributesFrozen = True
            getattr(self, t)._dataFrozen  = True
            getattr(self, t)._attributesFrozen = True
        self._isFrozen = True

class TicDatFactory(freezableFactory(object, "_isFrozen")) :
    def __init__(self, primaryKeyFields = {}, dataFields = {}):
        primaryKeyFields, dataFields = _utls.checkSchema(primaryKeyFields, dataFields)

        assert set(dataFields).issubset(primaryKeyFields), "this code assumes all tables have primary keys"
        dataRowFactory = FrozenDict({t : _utls.ticDataRowFactory(t, primaryKeyFields[t], dataFields.get(t, ()))
                            for t in primaryKeyFields})

        class FrozenTicDat(_TicDat) :
            def __init__(self, **initTables):
                for t in initTables :
                    verify(t in set(primaryKeyFields).union(dataFields), "Unexpected table name %s"%t)
                for t,v in initTables.items():
                    badTicDatTable = []
                    if not (goodTicDatTable(v, lambda x : badTicDatTable.append(x))) :
                        raise _utls.TicDatError(t + " cannot be treated as a ticDat table : " + badTicDatTable[-1])
                    for _k in v.keys():
                        verify((hasattr(_k, "__len__") and len(_k) == len(primaryKeyFields.get(t, ())) or
                               len(primaryKeyFields.get(t, ())) == 1),
                           "Unexpected number of primary key fields for %s"%t)
                    # lots of verification inside the dataRowFactory
                    setattr(self, t, FrozenDict({_k : dataRowFactory[t](_v) for _k, _v in v.items() }))
                    for v in getattr(self, t).values() :
                        v._dataFrozen =True
                        v._attributesFrozen = True
                for t in set(primaryKeyFields).union(dataFields).difference(initTables) :
                    setattr(self, t, FrozenDict())
                self._isFrozen = True
            def __repr__(self):
                return "td:" + tuple(set(primaryKeyFields).union(dataFields).keys()).__repr__()
        self.FrozenTicDat = FrozenTicDat

        self._isFrozen = True


def datDictFactory(dataRowFactory) :
    class StaticTableDict (_utls.FreezeableDict) :
        def __setitem__(self, key, value):
            verify(_utls.dictish(value), "the values of a TableDict should all be parallel dictionaries")
            return super(StaticTableDict, self).__setitem__(key, dataRowFactory(value))


def goodTicDatObject(ticDatObject, tableList = None, badMessageHolder=None):
    if tableList is None :
        tableList = tuple(x for x in dir(ticDatObject) if not x.startswith("_") and
                          not callable(getattr(ticDatObject, x)))
    badMessages = badMessageHolder if badMessageHolder is not None else  []
    assert hasattr(badMessages, "append")
    def _hasAttr(t) :
        if not hasattr(ticDatObject, t) :
            badMessages.append(t + " not an attribute.")
            return False
        return True
    evalGood = (_hasAttr(t) and goodTicDatTable(getattr(ticDatObject, t),
                lambda x : badMessages.append(t + " : " + x)) for t in tableList)
    if (badMessageHolder is not None) : # if logging, then evaluate all, else shortcircuit
        evalGood = list(evalGood)
    return all(evalGood)

def goodTicDatTable(ticDatTable, badMessageHandler = lambda x : None):
    if not _utls.dictish(ticDatTable) :
        badMessageHandler("Not a dict-like object.")
        return False
    if not len(ticDatTable) :
        return True
    def keyLen(k) :
        if not _utls.containerish(k) :
            return "singleton"
        try:
            rtn = len(k)
        except :
            rtn = 0
        return rtn
    if not all(keyLen(k) == keyLen(ticDatTable.keys()[0]) for k in ticDatTable.keys()) :
        badMessageHandler("Inconsistent key lengths")
        return False
    dictishRows = tuple(x for x in ticDatTable.values() if _utls.dictish(x))
    if not all(set(x.keys()) == set(dictishRows[0].keys()) for x in dictishRows) :
        badMessageHandler("Inconsistent data field name keys.")
        return False
    containerishRows = tuple(x for x in ticDatTable.values() if _utls.containerish(x) and not  _utls.dictish(x))
    if (not all(len(x) == len(containerishRows[0]) for x in containerishRows) or
        (containerishRows and dictishRows and len(containerishRows[0]) != len(dictishRows[0]) ) ) :
        badMessageHandler("Inconsistent data row lengths.")
        return False
    singletonishRows = tuple(x for x in ticDatTable.values() if not (_utls.containerish(x) or _utls.dictish(x)))
    if singletonishRows and any(len(x) != 1 for x in containerishRows + dictishRows) :
        badMessageHandler("At least one value is not a dict-like object")
        return False
    return True

def freezeMe(x) :
    """
    Freezes a
    :param x: ticDat object
    :return: x, after it has been frozen
    """
    if not getattr(x, "_isFrozen", True) : #idempotent
        x._freeze()
    return x