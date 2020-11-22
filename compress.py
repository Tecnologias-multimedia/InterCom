import zlib
import argparse
import buffer
import argcomplete  # <tab> completion for argparse.

class Compress(buffer.Buffering):

    def __init__(self):
        super().__init__()

    # We have to overwrite this method
    def pack(self, chunk_number, chunk):
        return super().pack(chunk_number, chunk)

    # We have to overwrite this method
    def unpack(self, packed_chunk,
               dtype=buffer.minimal.Minimal.SAMPLE_TYPE):
        return super().unpack(packed_chunk, dtype)


if __name__ == "__main__":
    buffer.minimal.parser.description = __doc__
    argcomplete.autocomplete(buffer.minimal.parser)
    buffer.minimal.args = buffer.minimal.parser.parse_known_args()[0]
    intercom = Compress()
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        buffer.minimal.parser.exit(1)
