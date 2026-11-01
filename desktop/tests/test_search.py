from hzdesktop.retrieval import search, phi, hz_refine, lexical_vector


def test_deterministic_retrieval():
    records = [{'id':'001','title':'Dentist','content':'Dentist appointment Thursday at 2pm','source':'note'},
               {'id':'002','title':'Shopping','content':'Buy milk and orange juice','source':'note'}]
    first = search(records, 'dentist appointment thursday')
    second = search(records, 'dentist appointment thursday')
    assert first == second
    assert first[0]['record']['id'] == '001'
    assert search(records, '   ') == []


def test_hinge_refinement_changes_vector():
    query = lexical_vector('broken refrigerator freezer')
    candidates = [lexical_vector('refrigerator freezer'), lexical_vector('car wheel')]
    a = hz_refine(query, candidates, steps=2)
    b = hz_refine(query, candidates, steps=2)
    assert a == b
    assert a != hz_refine(query, candidates, steps=0)
    assert phi(0.0) == 0.0
