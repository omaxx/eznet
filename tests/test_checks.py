from eznet.check import define_check


def test_define_check():
    @define_check
    def func():
        pass
