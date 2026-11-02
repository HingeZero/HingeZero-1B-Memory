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


def test_mixed_embeddings_never_mix_incompatible_vector_spaces():
    # The old implementation crashed with IndexError when one record had
    # a 32-dimensional semantic embedding and another used 256-dim lexical.
    rows = [
        {'id':'1','title':'summer project','content':'milestone today',
         'embedding_model':'embeddinggemma','embedding':[1.0]+[0.0]*31},
        {'id':'2','title':'summer project','content':'milestone tomorrow'},
    ]
    query = [1.0]+[0.0]*31
    a = search(rows,'summer project',query_embedding=query,embedding_model='embeddinggemma')
    b = search(rows,'summer project',query_embedding=query,embedding_model='embeddinggemma')
    assert a and a == b
    assert {item['record']['id'] for item in a} == {'1', '2'}


def test_all_semantic_embeddings_share_one_refinement_space():
    rows = [
        {'id':'1','title':'project alpha','content':'task completed',
         'embedding_model':'embeddinggemma','embedding':[1.0]+[0.0]*31},
        {'id':'2','title':'project beta','content':'task planned',
         'embedding_model':'embeddinggemma','embedding':[0.0,1.0]+[0.0]*30},
    ]
    result = search(rows,'project',query_embedding=[1.0]+[0.0]*31,
                    embedding_model='embeddinggemma')
    assert result and result[0]['record']['id'] == '1'
