from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json


# Options pour Chrome
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Exécuter en mode headless (sans interface graphique)

# Démarrer Chrome avec Selenium
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # Ouvrir YouTube et se connecter (si nécessaire)
    driver.get('https://www.youtube.com')
    time.sleep(10)  # Attendre que la page se charge

    # Exporter les cookies
    cookies = driver.get_cookies()

    # Sauvegarder les cookies dans un fichier au format Netscape
    with open('cookies.txt', 'w') as f:
        for cookie in cookies:
            f.write(
                f"{cookie['domain']}\t"
                f"{'TRUE' if cookie['domain'].startswith('.') else 'FALSE'}\t"
                f"{cookie['path']}\t"
                f"{'TRUE' if cookie['secure'] else 'FALSE'}\t"
                f"{int(cookie['expiry']) if 'expiry' in cookie else '0'}\t"
                f"{cookie['name']}\t"
                f"{cookie['value']}\n"
            )

    print("✅ Cookies exportés avec succès dans cookies.txt")

finally:
    # Fermer le navigateur
    driver.quit()
