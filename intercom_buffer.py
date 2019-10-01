from intercom import Intercom

class Intercom_buffer(Intercom):

    def init(self, args):
        Intercom.init(self, args)


if __name__ == "__main__":
    intercom = Intercom_buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
