import os

from dotenv import load_dotenv

load_dotenv(override=True)

MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")

ALIYUN_BASE_URL = os.getenv("ALIYUN_BASE_URL")
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY")


def main():
    print(f"MINIMAX_BASE_URL: {MINIMAX_BASE_URL}")
    print(f"MINIMAX_API_KEY: {MINIMAX_API_KEY}")


if __name__ == "__main__":
    main()
