import pytest
from archie.answer import _validate_shape

def test_rejects_invented_evidence_id():
    obj={'status':'VERIFIED','answer':'x','claims':[{'text':'x','evidence_ids':['FAKE'],'kind':'DIRECT'}]}
    with pytest.raises(ValueError): _validate_shape(obj,{'SRD521-P001-C01'})

def test_verified_requires_claims():
    with pytest.raises(ValueError): _validate_shape({'status':'VERIFIED','answer':'x','claims':[]},{'A'})

def test_accepts_bound_claim():
    c=_validate_shape({'status':'DERIVED','answer':'x','claims':[{'text':'x','evidence_ids':['A'],'kind':'DERIVED'}]},{'A'})
    assert len(c)==1
