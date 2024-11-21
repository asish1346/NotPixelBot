import random


def generate_user_agent():
    device_android_versions = {
        "Pixel 7 Pro": ["13.0", "12.0"],
        "Pixel 7": ["13.0", "12.0"],
        "Pixel 6 Pro": ["13.0", "12.0", "11.0"],
        "Pixel 6": ["13.0", "12.0", "11.0"],
        "Pixel 5": ["13.0", "12.0", "11.0", "10.0"],
        "Samsung Galaxy S23": ["13.0", "12.0"],
        "Samsung Galaxy S23 Ultra": ["13.0", "12.0"],
        "Samsung Galaxy S22": ["13.0", "12.0", "11.0"],
        "Samsung Galaxy S21": ["13.0", "12.0", "11.0", "10.0"],
        "Samsung Galaxy S20": ["13.0", "12.0", "11.0", "10.0"],
        "OnePlus 11": ["13.0", "12.0"],
        "OnePlus 10 Pro": ["13.0", "12.0"],
        "OnePlus 9": ["13.0", "12.0", "11.0"],
        "OnePlus 8T": ["13.0", "12.0", "11.0"],
        "Xiaomi 13 Pro": ["13.0", "12.0"],
        "Xiaomi 12": ["13.0", "12.0", "11.0"],
        "Xiaomi Mi 11": ["13.0", "12.0", "11.0"],
        "Huawei P50 Pro": ["13.0", "12.0", "11.0"],
        "Huawei Mate 40 Pro": ["13.0", "12.0", "11.0"],
        "Sony Xperia 1 V": ["13.0", "12.0"],
        "Sony Xperia 5 III": ["13.0", "12.0", "11.0"],
        "Oppo Find X5 Pro": ["13.0", "12.0"],
        "Oppo Find X3 Pro": ["13.0", "12.0", "11.0"],
        "Realme GT 2 Pro": ["13.0", "12.0"],
        "Realme X50 Pro": ["12.0", "11.0"],
    }

    chrome_major_version = random.randint(110, 128)
    chrome_minor_version = random.randint(0, 9999)
    chrome_build_version = random.randint(0, 9999)
    chrome_version = (
        f"{chrome_major_version}.0.{chrome_minor_version}.{chrome_build_version}"
    )

    device = random.choice(list(device_android_versions.keys()))

    android_version = random.choice(device_android_versions[device])

    user_agent = f"Mozilla/5.0 (Linux; Android {android_version}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Mobile Safari/537.36"

    return user_agent
