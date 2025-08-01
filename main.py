from pyrogram import Client
from config import api_hash, api_id
from colorama import init, Fore, Style
import traceback
import argparse
import asyncio
import os
workdir = os.path.join(os.getcwd(), "sessions")
os.makedirs(workdir, exist_ok=True)
init(autoreset=True)

app = Client("session", api_id=api_id, api_hash=api_hash, workdir=workdir)
async def main():
  parser = argparse.ArgumentParser(description="Telegram autobuy bot CLI")
  parser.add_argument(
    "--id",
    type=int,
    required=False,
    help="gift ID to snipe (filter)",
  )
  parser.add_argument(
    "--price",
    type=int,
    required=False,
    help="price in TGStars to snipe (filter)",
  )
  parser.add_argument(
    "--total_amount",
    type=int,
    required=False,
    help="total amount of gift available to snipe (filter)",
  )
  parser.add_argument(
    "--check_every",
    type=int,
    required=False,
    default=60,
    help="check gifts every n seconds",
  )
  args = parser.parse_args()
  
  filters = {
    "limited": True
  }
  if args.id is not None:
    print(Fore.GREEN + Style.DIM + f"* set ID={args.id}")
    filters["id"] = args.id

  if args.price is not None:
    print(Fore.GREEN + Style.DIM + f"* set PRICE={args.price}")
    filters["price"] = args.price

  if args.total_amount is not None:
    print(Fore.GREEN + Style.DIM + f"* set TOTAL_AMOUNT={args.total_amount}")
    filters["total_amount"] = args.total_amount

  async with app:
    me = await app.get_me()
    print(Fore.GREEN + Style.DIM + f"* Bot is connected to | {me.phone_number}:{me.username} |...\n")

    while True:
      try:
        gifts = await app.get_available_gifts()
        if filters.get("limited") is not None:
          gifts = filter(lambda g: g.is_limited == filters.get("limited"), gifts)
        
        if filters.get("sold_out") is not None:
          gifts = filter(lambda g: g.is_sold_out == filters.get("sold_out"), gifts)

        if filters.get("id") is not None:
          gifts = filter(lambda g: g.id == filters.get("id"), gifts)

        if filters.get("price") is not None:
          gifts = filter(lambda g: g.price == filters.get("price"), gifts)

        if filters.get("total_amount") is not None:
          gifts = filter(lambda g: g.total_amount == filters.get("total_amount"), gifts)

        gifts = list(gifts)
        entries = len(gifts)
        if entries <= 0:
          print(Fore.RED + Style.DIM + f"Nothing found, waiting {args.check_every} secs...")
          await asyncio.sleep(args.check_every)
          continue

        if entries > 1:
          print(Fore.YELLOW + Style.DIM + f"Found {entries} entries, using the first one")
        gift = gifts[0]

        print(f"id: {gift.id}, e: {gift.sticker.emoji}, price: {gift.price}, sold_out: {gift.is_sold_out}, total_amount: {gift.total_amount}, limited: {gift.is_limited}")
        return
      except Exception as e:
        tb_str = traceback.format_exc()
        print(f"err: {e} / {tb_str}")
    
if __name__ == "__main__":
  app.run(main())

