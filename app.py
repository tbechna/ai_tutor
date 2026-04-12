import streamlit as st
import streamlit.components.v1 as components
import os
import json
from openai import OpenAI
import sympy as sp

#funkce
from fce import token_count, vypocet_integralu

#pripojeni pres api
client = OpenAI(
    api_key=st.secrets["einfra"]["api_key"],
    base_url="https://llm.ai.e-infra.cz/v1"
)
model_id = 'deepseek-v3.2'
  # instrukce ze souboru
# try:
 #   with open('tutor_config.json', 'r', encoding='utf-8') as f:
  #      tutor_data = json.load(f)
    
   # persona = tutor_data.get("tutor_persona", {})
    #pravidla = "\n- ".join(tutor_data.get("format_vystupu", {}).get("pravidla", [])) # seznam
    #scenare = json.dumps(tutor_data.get("scenare", {}), indent=2, ensure_ascii=False) #vnoreny slovnik
    #znalosti = json.dumps(tutor_data.get("knowledge_base", {}), indent=2, ensure_ascii=False) #vnoreny slovnik

    #system_instrukce = (
       # f"Jsi AI tutor integrálního počtu.\n"
        #f"ROLE: {persona.get('role')}\n"
        #f"CÍL: {persona.get('cil')}\n"
        #f"TÓN: {persona.get('ton')}\n\n"
        #f"POVINNÁ PRAVIDLA:\n- {pravidla}\n\n"
        #f"POVINNÉ REAKCE NA SITUACE:\n{scenare}\n\n"
        #f"ZNALOSTNÍ BÁZE:\n{znalosti}") """

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
    </style>
""", unsafe_allow_html=True)

# ukladani historie a konverzace
if 'historie' not in st.session_state: #sidebar - seznam prikladu
    st.session_state.historie = []
if "messages" not in st.session_state: #konverzace - seznam zprav
    st.session_state.messages = []

#nastaveni klavesnice
cesta_ke_slozce = os.path.join(os.path.dirname(__file__), "klavesnice")
matematicka_klavesnice = components.declare_component(
    "matematicka_klavesnice", 
    path=cesta_ke_slozce
)

# zadaní integralu
if "aktualni_fce" not in st.session_state:
    st.subheader('Zadání integrálu')

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

if "aktualni_fce" in st.session_state:
    # Změníme lehce poměr sloupců, aby mělo tlačítko dost místa
    col_latex, col_btn = st.columns([0.8, 0.2])
    
    with col_latex:
        # Text dáme normálně a na další řádek vložíme čistý latexový blok
        st.markdown("**Aktuální zadání:**")
        st.latex(rf"\int {sp.latex(st.session_state.aktualni_fce)} \, dx")

    with col_btn:
        st.write("") # Tento prázdný řádek vizuálně zarovná tlačítko s nadpisem
        if st.button("Nové zadání", use_container_width=True):
            del st.session_state.aktualni_fce
            del st.session_state.spravny_vysledek
            st.session_state.messages = []
            st.rerun()

    #zpravicky
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

#prompty od studenta
    if prompt := st.chat_input("Napiš postup nebo se zeptej na radu."):
    # zobrazení promptu a vlozeni do konverzace - with je bublina

        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt })


        septani = f"ZADÁNÍ INTEGRÁLU: {str(st.session_state.aktualni_fce)}. VÝSLEDEK: {str(st.session_state.spravny_vysledek)}"
        api_messages = [{"role": "system", "content": system_instrukce + '\n\n' + septani }] + st.session_state.messages
        
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
    st.subheader("Využití tokenů")
    tokens = token_count(system_instrukce, st.session_state.messages, model_id)
    st.metric("Využité tokeny", f"{tokens}")
    st.progress(min(tokens / 10000, 1.0))

    st.divider()
    
   # st.subheader("Historie výpočtů")
    #for polozka in st.session_state.historie:
     #   with st.container():
     #       neurcity_vysledek = sp.latex(polozka['vysledek']) + "+ C"
      #      st.latex(rf"\int {sp.latex(polozka['zadani'])} \, dx = {neurcity_vysledek}")
       # st.divider() 
    
    st.subheader("Uložení dat")
    historie_json = json.dumps(st.session_state.messages, ensure_ascii=False, indent=4)
    st.download_button(
        label="Stáhnout historii chatu (JSON)",
        data=historie_json,
        file_name="historie_tutora.json",
        mime="application/json"
    )

    if st.button("Resetovat konverzaci"):
        st.session_state.messages = []
        st.session_state.historie = []
        st.rerun() # reset s prazdnou pameti
   