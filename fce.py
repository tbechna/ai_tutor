import tiktoken, math
import sympy as sp
from sympy import Symbol, sin, integrate, parse_expr
from sympy.integrals.manualintegrate import integral_steps

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