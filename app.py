import streamlit as st
import streamlit.components.v1 as components
import os
import json
from openai import OpenAI
import sympy as sp
from rich import print as rprint
from rich.pretty import pprint as rpprint

#funkce
from fce import token_count, vypocet_integralu, ulozit_do_sheets, ulozit_do_github

#pripojeni pres api
client = OpenAI(
    api_key=st.secrets["einfra"]["api_key"],
    base_url="https://llm.ai.e-infra.cz/v1"
)
model_id = 'deepseek-v4-pro'
  # instrukce ze souboru

with open("tutor_config.md", "r", encoding="utf-8") as f:
    system_instrukce = f.read()
    
#______________________________________________________________________________________________________________
    #STREAMLIT
st.set_page_config(page_title="AI tutor")
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 0rem;
        }
        .stAlert {
            padding-top: 1.2rem;
        }
    </style>
""", unsafe_allow_html=True)

# inicializace konverzace a hodnoceni
if "messages" not in st.session_state: #konverzace - seznam zprav
    st.session_state.messages = []
if "hodnoceni_dialog" not in st.session_state: #hodnoceni
    st.session_state.hodnoceni_dialog = False

#nastaveni klavesnice
cesta_ke_slozce = os.path.join(os.path.dirname(__file__), "klavesnice")
matematicka_klavesnice = components.declare_component(
    "matematicka_klavesnice", 
    path=cesta_ke_slozce
)

# zadaní integralu
if "aktualni_fce" not in st.session_state:
    st.info("""
    Jak chatbot funguje:
    - Zadejte funkci proměnné $x$, jejíž neurčitý integrál chcete zjistit. Chatbot vás provede řešením.
    - Po vyřešení ohodnoťte chatbota. Konverzace a hodnocení se poté automaticky ukládá pro účely diplomové práce.
    """)

    vstup = matematicka_klavesnice()

    if vstup:
        zadani, vysledek, chyba = vypocet_integralu(vstup)
        if chyba:
            st.error(chyba)
        else:  
                # ulozeni do pameti jako sympy
            st.session_state.aktualni_fce = zadani
            st.session_state.spravny_vysledek = vysledek     
            st.session_state.messages = [
                    {"role": "assistant", "content": f"Budeme integrovat funkci ${sp.latex(zadani)}$. Napadá tě, jak postupovat?"}
                ]           
            st.rerun() 

if "aktualni_fce" in st.session_state: # po zadani integralu

    #vykresleni zadani
    st.markdown("**Aktuální zadání:**")
    st.latex(rf"\int {sp.latex(st.session_state.aktualni_fce)} \, dx")

    #zpravicky
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    #hodnoceni
    if not st.session_state.hodnoceni_dialog:
        if st.button("Nový příklad a zhodnocení chatbota"):
            st.session_state.hodnoceni_dialog = True
            st.rerun()
    else: #hodnoceni
        st.info("Jak moc ti chatbot pomohl pochopit postup?")
        hodnoceni_skala = st.select_slider(
            "Hodnocení:",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {
                1: "1 - vůbec nepomohl",
                2: "2",
                3: "3",
                4: "4",
                5: "5 - velmi pomohl"
            }[x]
        )

        komentar = st.text_area(
            "Narazil/a jsi na něco, co tě zmátlo nebo co chatbot špatně vysvětlil?",
            placeholder="Napiš komentář..."
        )

        zpracovava = st.session_state.get("zpracovava", False)

        if st.button("Odeslat hodnocení", disabled=zpracovava):
            st.session_state.zpracovava = True
            fce_pro_ulozeni = st.session_state.get("aktualni_fce")
            zpravy_pro_ulozeni = st.session_state.messages.copy()
            del st.session_state.aktualni_fce
            del st.session_state.spravny_vysledek
            st.session_state.messages = []
            st.session_state.hodnoceni_dialog = False
            st.session_state.zpracovava = False
            
            chyba_ulozeni = []

            try:
                ulozit_do_sheets(
                    st.secrets,
                    fce_pro_ulozeni,
                    hodnoceni=str(hodnoceni_skala),
                    komentar=komentar
                )
            except Exception as e:
                chyba_ulozeni.append(f"Google Sheets: {e}")

            try:
                ulozit_do_github(
                    st.secrets,
                    fce_pro_ulozeni,
                    zpravy_pro_ulozeni,
                    hodnoceni=str(hodnoceni_skala),
                    komentar=komentar
                )
            except Exception as e:
                chyba_ulozeni.append(f"GitHub: {e}")

            if chyba_ulozeni:
                st.error("Nepodařilo se uložit data: " + ", ".join(chyba_ulozeni))
    
    #prompt od studenta
    if prompt := st.chat_input("Napiš postup nebo se zeptej na radu.", disabled=st.session_state.hodnoceni_dialog): #tlacitko novy priklad --> hodnoceni dialog je TRUE
    # zobrazení promptu a vlozeni do konverzace - with je bublina

        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt })


        septani = f"ZADÁNÍ INTEGRÁLU: {str(st.session_state.aktualni_fce)}. VÝSLEDEK: {str(st.session_state.spravny_vysledek)}"
        api_messages = [{"role": "system", "content": system_instrukce + '\n\n' + septani }] + st.session_state.messages[-10:]
        
    #volani ai
        with st.chat_message("assistant"):
            try:
                odpoved = client.chat.completions.create(
                    model=model_id, 
                    messages=api_messages,
                )  

                txt_odpovedi = odpoved.choices[0].message.content
                st.markdown(txt_odpovedi)
                
                st.session_state.messages.append({"role": "assistant", "content": txt_odpovedi })

            except Exception as e:
                st.error(f"Omlouvám se, došlo k chybě: {e}")
#____________________________________________________________________________________________________________________________

# sidebar - historie vypoctu a reset konverzace
with st.sidebar:
    debug_mode = st.secrets.get("debug", False)
    
    if debug_mode: #to vidim jen ja
        tokens = token_count(system_instrukce, st.session_state.messages, model_id)
        st.metric("Využité tokeny", f"{tokens}")
        st.progress(min(tokens / 10000, 1.0))
        st.divider()
    
    historie_json = json.dumps(st.session_state.messages, ensure_ascii=False, indent=4)
    st.download_button(
        label="Stáhnout historii chatu (JSON)",
        data=historie_json,
        file_name="historie_tutora.json",
        mime="application/json"
    )

    if st.button("Resetovat konverzaci"):
        st.session_state.messages = []
        st.session_state.pop("aktualni_fce", None)
        st.session_state.pop("spravny_vysledek", None)
        st.rerun()
rpprint(dict(st.session_state), expand_all=True)