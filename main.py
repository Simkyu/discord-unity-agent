import config
from agent.session import AgentSession
from bot.client import create_client


def main() -> None:
    session = AgentSession()
    client = create_client(session)
    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
