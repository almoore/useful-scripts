from vercmp import debian_compare


def test_debian_compare():
    assert debian_compare("", "") == 0
    assert debian_compare("~~", "~~a") < 0
    assert debian_compare("~", "~~a") > 0
    assert debian_compare("~", "") < 0
    assert debian_compare("a", "") > 0
    assert debian_compare("1.2.3~rc1", "1.2.3") < 0
    assert debian_compare("1.2", "1.2") == 0
    assert debian_compare("1.2", "a1.2") < 0
    assert debian_compare("1.2.3", "1.2-3") > 0
    assert debian_compare("1.2.3~rc1", "1.2.3~~rc1") > 0
    assert debian_compare("1.2.3", "2") < 0
    assert debian_compare("2.0.0", "2.0") > 0
    assert debian_compare("1.2.a", "1.2.3") > 0
    assert debian_compare("1.2.a", "1.2a") > 0
    assert debian_compare("1", "1.2.3.4") < 0
    assert debian_compare("1:2.3.4", "1:2.3.4") == 0
    assert debian_compare("0:", "0:") == 0
    assert debian_compare("0:", "") == 0
    assert debian_compare("0:1.2", "1.2") == 0
    assert debian_compare("0:", "1:") < 0
    assert debian_compare("0:1.2.3", "2:0.4.5") < 0
