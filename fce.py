import tiktoken, math
import sympy as sp
from sympy import Symbol, sin, integrate, parse_expr
from sympy.integrals.manualintegrate import integral_steps
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

#tokeny
def token_count(system_instrukce, messages, model_id):
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # 2. Spojíme texty
        full_text = system_instrukce + str(messages)
        
        # 3. Spočítáme základní tokeny
        zakladni_tokeny = len(encoding.encode(full_text))
        
        # 4. PŘIDÁNÍ REZERVY: DeepSeek tokenizuje mírně jinak, přidáme 5 % pro jistotu
        # a zaokrouhlíme to nahoru na celé číslo
        tokeny_s_rezervou = math.ceil(zakladni_tokeny * 1.05)
        
        return tokeny_s_rezervou
    except Exception:
        return 0
    
#vypocet integralu
def vypocet_integralu(zadani):
    x = sp.Symbol('x')
    try:
        fce = parse_expr(zadani) #vrati zadani jako Sympy
        nezname = fce.free_symbols
        nezname.discard(x)

        if nezname: #prazdna mn. je bool false
            return None, None, "Zkontroluj si prosím, že zadáváš funkci, ne text."
        
        vysledek = integrate(fce, x)

        if isinstance(vysledek, sp.Integral): # neresitelny intergral
            return None, None, "Tento integrál nelze vyjádřit pomocí elementárních funkcí."
        
        return fce, vysledek, None
    
    except Exception:
        return None, None, "Zkontroluj si prosím syntaxi. je to správně matematicky?"
    
def ulozit_do_sheets(secrets, zadani, hodnoceni=None, komentar=None):
    try:
        creds = Credentials.from_service_account_info(
            dict(secrets["gcp_service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(secrets["sheets"]["sheet_id"]).sheet1

        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(zadani),
            hodnoceni or "",
            komentar or ""
        ])

    except Exception as e:
        print(f"Sheets chyba: {e}")

def ulozit_do_github(secrets, zadani, messages, hodnoceni=None, komentar=None):
    try:
        import requests, base64

        obsah = {
            "timestamp": datetime.now().isoformat(),
            "zadani": str(zadani),
            "hodnoceni": hodnoceni or "",
            "komentar": komentar or "",
            "konverzace": messages
        }
        obsah_json = json.dumps(obsah, ensure_ascii=False, indent=2).encode("utf-8")
        nazev = f"{secrets['github']['slozka']}/chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        url = f"https://api.github.com/repos/{secrets['github']['repo']}/contents/{nazev}"
        response = requests.put(
            url,
            headers={"Authorization": f"token {secrets['github']['token']}"},
            json={
                "message": f"chat log {datetime.now().isoformat()}",
                "content": base64.b64encode(obsah_json).decode()
            }
        )
        if response.status_code != 201:
            print(f"GitHub chyba: {response.json()}")

    except Exception as e:
        print(f"GitHub chyba: {e}")