import os
import shutil
import sys
import time

not_pixel_text_art = """
███╗   ██╗ ██████╗ ████████╗    ██████╗ ██╗██╗  ██╗███████╗██╗     
████╗  ██║██╔═══██╗╚══██╔══╝    ██╔══██╗██║╚██╗██╔╝██╔════╝██║     
██╔██╗ ██║██║   ██║   ██║       ██████╔╝██║ ╚███╔╝ █████╗  ██║     
██║╚██╗██║██║   ██║   ██║       ██╔═══╝ ██║ ██╔██╗ ██╔══╝  ██║     
██║ ╚████║╚██████╔╝   ██║       ██║     ██║██╔╝ ██╗███████╗███████╗
╚═╝  ╚═══╝ ╚═════╝    ╚═╝       ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝  

\033[33mVersion:- 4.0\033[0m
"""

capybara_society_art = """

  ('-.      .-')    ('-. .-.             
  ( OO ).-. ( OO ). ( OO )  /             
  / . --. /(_)---\_),--. ,--. ,--. ,--.   
  | \-.  \ /    _ | |  | |  | |  | |  |   
.-'-'  |  |\  :` `. |   .|  | |  | | .-') 
 \| |_.'  | '..`''.)|       | |  |_|( OO )
  |  .-.  |.-._)   \|  .-.  | |  | | `-' /
  |  | |  |\       /|  | |  |('  '-'(_.-' 
  `--' `--' `-----' `--' `--'  `-----'  
"""

capybara_society_text_art = """

  ('-.      .-')    ('-. .-.             
  ( OO ).-. ( OO ). ( OO )  /             
  / . --. /(_)---\_),--. ,--. ,--. ,--.   
  | \-.  \ /    _ | |  | |  | |  | |  |   
.-'-'  |  |\  :` `. |   .|  | |  | | .-') 
 \| |_.'  | '..`''.)|       | |  |_|( OO )
  |  .-.  |.-._)   \|  .-.  | |  | | `-' /
  |  | |  |\       /|  | |  |('  '-'(_.-' 
  `--' `--' `-----' `--' `--'  `-----'  
"""


def print_banner_slowly(banner: str, delay: float = 0.003) -> None:
    for char in banner:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)


def blink_banner(banner: str, blink_times: int = 5, blink_delay: float = 0.5) -> None:
    for _ in range(blink_times):
        clear_screen()
        time.sleep(blink_delay)
        print(banner)
        time.sleep(blink_delay)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def get_terminal_size() -> os.terminal_size:
    return shutil.get_terminal_size()


def is_terminal_too_small(
    width: int, height: int, min_width: int, min_height: int
) -> bool:
    return width < min_width or height < min_height


def print_banner_animation() -> None:
    clear_screen()

    size = get_terminal_size()

    if is_terminal_too_small(size.columns, size.lines, 90, 23):
        banner = capybara_society_text_art
    else:
        banner = capybara_society_art

    print_banner_slowly(banner)
    blink_banner(banner)

    clear_screen()

    print_banner_slowly(not_pixel_text_art)
