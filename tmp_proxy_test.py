import asyncio
from apify import Actor


async def main() -> None:
    async with Actor:
        try:
            proxy_config = await Actor.create_proxy_configuration(
                groups=["RESIDENTIAL"],
                country_code="US",
            )
            print("proxy_config", proxy_config)
            proxy_url = await proxy_config.new_url()
            print("proxy_url", proxy_url)
        except Exception as exc:
            print("proxy_error", exc)


asyncio.run(main())
