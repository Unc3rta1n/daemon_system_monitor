import asyncio

from grpc_.server import serve
from utils.utils import parse_args, init_logging

if __name__ == "__main__":
    args = parse_args()
    init_logging()

    if args.port:
        asyncio.run(serve(port=args.port))
    else:
        asyncio.run(serve())
