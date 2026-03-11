import sys
from core.orchestrator import processUserRequest

def printBanner():
    banner = """
    =========================================================================
    🧵 L.O.O.M. (Layered Orchestration & Operational Mind)
    =========================================================================
    System: Fedora Linux (WayLand)
    Status: ONLINE
    Type 'exit' or 'quit' to shutdown.
    -------------------------------------------------------------------------
"""

    print(banner)


def main():
    printBanner()

    while True:
        try:
            userInput = input("\n👤 You: ")

            if userInput.lower() in ["exit", "quit"]:
                print("Shutting Down L.O.O.M.....")
                sys.exit(0)

            if not userInput.strip():
                continue

            processUserRequest(userInput)

        except KeyboardInterrupt:
            print("\n Force quitting LOOM..")
            sys.exit(0)

        except Exception as e:
            print("\n System Error: {e}")


if __name__ == "__main__":
    main()