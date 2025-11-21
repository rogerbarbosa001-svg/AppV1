import streamlit as st
import pandas as pd
import math
import plotly.express as px
import plotly.graph_objects as go
import json
import datetime
import uuid
import time
import smtplib
import random
import string
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Dict, Any, List
from urllib.parse import quote
import streamlit.components.v1 as components
# Importação condicional do gspread para evitar erro se não instalado
try:
    import gspread
except ImportError:
    gspread = None

# ==========================================
# 1. CONFIGURAÇÃO GERAL (PAI)
# ==========================================
st.set_page_config(
    page_title="SolarHíbrido Suite", 
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. ESTILOS CSS UNIFICADOS
# ==========================================
COR_PRIMARIA_PROP = "#3A6F1C"
COR_VERMELHO_PROP = "#D9534F"

st.markdown(f"""
    <style>
    /* --- CSS GERAL & BATERIAS --- */
    .stApp {{background-color: #f4f6f9;}}
    .stMetric {{background-color: #fff; border: 1px solid #dfe6e9; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}}
    div[data-testid="stExpander"] {{background-color: #fff; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);}}
    .project-header {{padding: 15px; background-color: #e3f2fd; border-radius: 8px; border-left: 5px solid #2196f3; margin-bottom: 20px;}}
    .warning-box {{padding: 10px; background-color: #ffebee; color: #c62828; border-radius: 5px; border: 1px solid #ef9a9a; margin-top: 10px;}}
    
    /* --- CSS PROPOSTAS --- */
    /* Botão Primário (Verde) */
    .st-emotion-cache-1v0mfe2.e10yg2x71, .st-emotion-cache-1l26i3s.e10yg2x71 {{
        background-color: {COR_PRIMARIA_PROP};
        border-color: {COR_PRIMARIA_PROP};
        color: white;
    }}
    .st-emotion-cache-1v0mfe2.e10yg2x71:hover, .st-emotion-cache-1l26i3s.e10yg2x71:hover {{
        background-color: #2E5916;
        border-color: #2E5916;
    }}
    /* Fontes personalizadas para métricas do Proposta */
    .metric-custom h4 {{ font-size: 1.0rem; font-weight: 400; color: #555; margin: 0; }}
    .metric-custom h3 {{ font-size: 1.4rem; font-weight: 700; color: #000; margin: 0; }}
    
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stButton"]) {{
        align-items: center;
    }}
    
    /* Estilo para caixas educativas */
    .educacao-box {{
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid {COR_PRIMARIA_PROP};
        margin-bottom: 15px;
    }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. FUNÇÕES DE AUTH E DB (DO CÓDIGO 1)
# ==========================================
EMAIL_SISTEMA = "brasilenertechmcz@gmail.com"       
SENHA_SISTEMA = "iypm cetf lrvd pyfa"    
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
DB_FILE = "users.json"

def carregar_usuarios_db():
    if not os.path.exists(DB_FILE):
        dados = {
            "admin@solar.com": {
                "pass": "admin", 
                "nome": "Administrador", 
                "email": "admin@solar.com", 
                "tel": "000"
            }
        }
        with open(DB_FILE, "w") as f: json.dump(dados, f)
        return dados
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}

def gerar_senha_forte():
    chars = string.ascii_letters + string.digits + "!@#"
    return ''.join(random.choice(chars) for i in range(8))

def enviar_senha_para_usuario(destinatario, nome, senha):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SISTEMA
        msg['To'] = destinatario
        msg['Subject'] = "🔐 Acesso SolarHíbrido Pro - Credenciais"

        corpo = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #f9f9f9; padding: 20px; border-radius: 10px;">
                <h2 style="color: #2980b9;">Bem-vindo, {nome}!</h2>
                <p>Seu cadastro foi realizado.</p>
                <hr>
                <p><b>Login (E-mail):</b> {destinatario}</p>
                <p><b>Senha Temporária:</b> <span style="background-color: #ddd; padding: 5px; font-weight: bold;">{senha}</span></p>
                <hr>
                <p>Use este e-mail e senha para acessar o sistema.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(corpo, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SISTEMA, SENHA_SISTEMA)
        server.sendmail(EMAIL_SISTEMA, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erro Email: {e}")
        return False

def registrar_usuario_automatico(nome, email, telefone):
    db = carregar_usuarios_db()
    if email in db:
        return False, "Este e-mail já possui cadastro."
    
    senha_nova = gerar_senha_forte()
    db[email] = {"pass": senha_nova, "nome": nome, "email": email, "tel": telefone}
    with open(DB_FILE, "w") as f: json.dump(db, f)
    
    enviou = enviar_senha_para_usuario(email, nome, senha_nova)
    if enviou:
        return True, "Cadastro Sucesso! A senha foi enviada para seu e-mail."
    else:
        return True, f"Conta criada, mas erro no envio de e-mail. Senha teste: {senha_nova}"

# ==========================================
# 4. TELA DE LOGIN (GLOBAL)
# ==========================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state: st.session_state['usuario_atual'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False

def tela_login():
    st.markdown("<br>", unsafe_allow_html=True)
    c_esq, c_centro, c_dir = st.columns([1, 1.2, 1])
    
    with c_centro:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>⚡ Solar Suite Login</h2>", unsafe_allow_html=True)
            
            tab_entrar, tab_criar = st.tabs(["🔑 Entrar", "📝 Criar Conta"])
            
            with tab_entrar:
                email_login = st.text_input("E-mail de Acesso", key="l_email")
                senha_login = st.text_input("Senha", type="password", key="l_pass")
                
                if st.button("Acessar Sistema", type="primary", use_container_width=True):
                    db = carregar_usuarios_db()
                    if email_login in db and db[email_login]['pass'] == senha_login:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = db[email_login]['nome']
                        st.session_state['is_admin'] = (email_login == "admin@solar.com")
                        st.success("Login Efetuado!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("E-mail ou Senha incorretos.")
            
            with tab_criar:
                st.info("Informe seu e-mail para receber a senha de acesso.")
                n_nome = st.text_input("Nome Completo")
                n_email = st.text_input("Seu Melhor E-mail")
                n_tel = st.text_input("Telefone")
                
                if st.button("Cadastrar e Receber Senha", use_container_width=True):
                    if n_nome and n_email:
                        if "@" not in n_email:
                            st.warning("Por favor, insira um e-mail válido.")
                        else:
                            ok, msg = registrar_usuario_automatico(n_nome, n_email, n_tel)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.warning("Preencha Nome e E-mail.")

if not st.session_state['logado']:
    tela_login()
    st.stop()

# ==========================================
# 5. NAVEGAÇÃO APÓS LOGIN
# ==========================================
with st.sidebar:
    st.title("Menu Principal")
    st.write(f"Olá, **{st.session_state['usuario_atual']}**")
    app_mode = st.radio("Selecione o Sistema:", 
        ["🔋 Dimensionamento Baterias", "☀️ Gerador de Propostas"]
    )
    st.markdown("---")
    if st.button("🚪 Sair (Logout)"):
        st.session_state['logado'] = False
        st.session_state['is_admin'] = False
        st.rerun()

# ==========================================
# 6. CÓDIGO DA APLICAÇÃO DE BATERIAS (Code A)
# ==========================================
def app_baterias():
    # --- INICIALIZAÇÃO DE DADOS (BATERIAS) ---
    if 'projeto_id' not in st.session_state: st.session_state['projeto_id'] = str(uuid.uuid4())[:8].upper()
    if 'projeto_data' not in st.session_state: st.session_state['projeto_data'] = datetime.datetime.now().strftime("%d/%m/%Y")

    if 'db_eletros' not in st.session_state:
        st.session_state['db_eletros'] = {
            "Personalizado": {"W": 0, "h": 0},
            "Lâmpada LED": {"W": 10, "h": 6},
            "Geladeira Inverter": {"W": 150, "h": 12},
            "Freezer Horizontal": {"W": 200, "h": 12},
            "TV 55 pol": {"W": 140, "h": 5},
            "Ar Cond. 9000 BTU": {"W": 850, "h": 8},
            "Ar Cond. 12000 BTU": {"W": 1100, "h": 8},
            "Ar Cond. 18000 BTU": {"W": 1600, "h": 8},
            "Roteador Wi-Fi": {"W": 30, "h": 24},
            "PC Desktop Gamer": {"W": 500, "h": 6},
            "Notebook": {"W": 65, "h": 8},
            "Microondas": {"W": 1400, "h": 0.3},
            "Máquina de Lavar": {"W": 500, "h": 1},
            "Câmeras CFTV (Kit)": {"W": 50, "h": 24},
            "Bomba Piscina 1/2cv": {"W": 750, "h": 4},
            "Chuveiro Elétrico": {"W": 5500, "h": 0.25},
            "Motor de Portão": {"W": 300, "h": 0.1}
        }

    if 'clientes' not in st.session_state: st.session_state['clientes'] = []
    if 'lista_cargas' not in st.session_state: st.session_state['lista_cargas'] = []

    if 'inversores' not in st.session_state:
        st.session_state['inversores'] = pd.DataFrame([
            {"Modelo": "GW3600-ES-BR20", "Tipo": "Híbrido LV", "Potencia_kW": 3.6, "Compatibilidade": "LV"},
            {"Modelo": "GW6000-ES-BR20", "Tipo": "Híbrido LV", "Potencia_kW": 6.0, "Compatibilidade": "LV"},
            {"Modelo": "GW12KL-ET", "Tipo": "Híbrido HV", "Potencia_kW": 12.0, "Compatibilidade": "HV"},
            {"Modelo": "GW15K-ET", "Tipo": "Híbrido HV", "Potencia_kW": 15.0, "Compatibilidade": "HV"},
            {"Modelo": "GW20K-ET", "Tipo": "Híbrido HV", "Potencia_kW": 20.0, "Compatibilidade": "HV"},
            {"Modelo": "GW30K-ET", "Tipo": "Híbrido HV", "Potencia_kW": 30.0, "Compatibilidade": "HV"},
        ]).sort_values(by="Potencia_kW")

    if 'baterias' not in st.session_state:
        st.session_state['baterias'] = pd.DataFrame([
            {"Modelo": "Lynx Home U (5.4 kWh)", "Tipo": "LV", "Capacidade_kWh": 5.4, "DoD": 0.90, "Compatibilidade": "LV"},
            {"Modelo": "Lynx F (G2) 3.27 kWh", "Tipo": "HV", "Capacidade_kWh": 3.27, "DoD": 0.90, "Compatibilidade": "HV"},
        ])

    if 'modulos' not in st.session_state:
        st.session_state['modulos'] = pd.DataFrame([
            {"Modelo": "RONMA 585W Bifacial", "Potencia_W": 585},
            {"Modelo": "DMEGC 605W Bifacial", "Potencia_W": 605},
            {"Modelo": "HANERSUN 610W", "Potencia_W": 610},
        ])

    # --- FUNÇÕES LÓGICAS (BATERIAS) ---
    def calcular_sistema(carga_total_kwh, pico_w, dias_autonomia, inv, bat, mod):
        eficiencia_inv = 0.95
        energia_nec = (carga_total_kwh * dias_autonomia) / (bat['DoD'] * eficiencia_inv)
        qtd_bat = math.ceil(energia_nec / bat['Capacidade_kWh'])
        
        qtd_pcu = 0
        msg_hv = ""
        if bat['Compatibilidade'] == 'HV':
            if qtd_bat < 2: 
                qtd_bat = 2 
                msg_hv = "Ajustado para min. 2 módulos (Tensão Mínima)."
            qtd_torres = math.ceil(qtd_bat / 9)
            qtd_pcu = qtd_torres
            msg_hv += f"Configuração: {qtd_torres} Torre(s) de até 9 módulos."
            
        banco_kwh = qtd_bat * bat['Capacidade_kWh']
        
        hsp = 4.8
        geracao_nec = carga_total_kwh / (hsp * 0.80)
        pot_fv_nec_kw = geracao_nec * 1.2
        qtd_mod = math.ceil((pot_fv_nec_kw * 1000) / mod['Potencia_W'])
        gerador_kwp = (qtd_mod * mod['Potencia_W']) / 1000
        
        ratio = (pico_w / 1000) / inv['Potencia_kW']
        status_inv = "✅ Ideal"
        if ratio > 1.0: status_inv = "⚠️ Sobrecarga (>100%)"
        elif ratio > 0.9: status_inv = "⚠️ Limite (>90%)"
        
        return {
            "qtd_bat": qtd_bat, "qtd_pcu": qtd_pcu, "banco_kwh": banco_kwh,
            "qtd_mod": qtd_mod, "gerador_kwp": gerador_kwp,
            "msg_hv": msg_hv, "status_inv": status_inv,
            "autonomia": (banco_kwh * bat['DoD']) / carga_total_kwh if carga_total_kwh > 0 else 0
        }

    def gerar_backup():
        return json.dumps({
            "clientes": st.session_state['clientes'],
            "lista_cargas": st.session_state['lista_cargas'],
            "projeto": {"id": st.session_state['projeto_id'], "data": st.session_state['projeto_data']}
        }, indent=4)

    def carregar_backup(file):
        try:
            d = json.load(file)
            st.session_state['clientes'] = d.get('clientes', [])
            st.session_state['lista_cargas'] = d.get('lista_cargas', [])
            st.session_state['projeto_id'] = d.get('projeto', {}).get('id', uuid.uuid4())
            return True
        except: return False

    # --- INTERFACE BATERIAS ---
    st.title("📐 Calculadora de Baterias Híbridas")
    
    abas_titulos = ["📐 Projeto", "👥 Clientes", "⚙️ Equipamentos", "💾 Backup"]
    if st.session_state['is_admin']:
        abas_titulos.append("🔑 Admin")

    tabs = st.tabs(abas_titulos)

    # ABA 1: PROJETO
    with tabs[0]:
        if not st.session_state['clientes']:
            st.warning("⚠️ Nenhum cliente cadastrado. Vá para a aba 'Clientes'.")
        else:
            c_sel_box = st.selectbox("Cliente:", [c['Nome'] for c in st.session_state['clientes']])
            dados_cli = next((c for c in st.session_state['clientes'] if c['Nome'] == c_sel_box), None)
            cidade_cli = dados_cli.get('Cidade', 'Não Informada') if dados_cli else "-"
            
            st.markdown(f"""
            <div class='project-header'>
                <div style="display: flex; justify-content: space-between;">
                    <div><b>👤 Cliente:</b> {c_sel_box} <br> <b>📍 Local:</b> {cidade_cli}</div>
                    <div style="text-align: right;"><b>🆔 ID:</b> {st.session_state['projeto_id']} <br> <b>📅 Data:</b> {st.session_state['projeto_data']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_in, col_out = st.columns([1, 1.4], gap="large")
            
            with col_in:
                st.markdown("#### 1. Cargas")
                with st.container(border=True):
                    opt = list(st.session_state['db_eletros'].keys())
                    sel = st.selectbox("Adicionar:", opt)
                    std = st.session_state['db_eletros'][sel]
                    
                    with st.form("add"):
                        c1, c2 = st.columns(2)
                        nm = c1.text_input("Item", value=sel)
                        pt = c2.number_input("Watts", value=std['W'])
                        c3, c4 = st.columns(2)
                        qt = c3.number_input("Qtd", 1, step=1)
                        hr = c4.number_input("h/Dia", value=float(std['h']), step=0.5)
                        
                        if st.form_submit_button("➕ Adicionar"):
                            st.session_state['lista_cargas'].append({
                                "Item": nm, "Potencia": pt, "Qtd": qt, "Horas": hr,
                                "Total_W": pt*qt, "Total_Wh": (pt*qt)*hr
                            })
                            st.rerun()
                
                if st.session_state['lista_cargas']:
                    df_ed = st.data_editor(
                        pd.DataFrame(st.session_state['lista_cargas']),
                        column_config={
                            "Total_W": st.column_config.NumberColumn("Tot W", disabled=True),
                            "Total_Wh": st.column_config.NumberColumn("Tot Wh", disabled=True)
                        },
                        num_rows="dynamic", key="editor", use_container_width=True
                    )
                    df_ed["Total_W"] = df_ed["Potencia"] * df_ed["Qtd"]
                    df_ed["Total_Wh"] = df_ed["Total_W"] * df_ed["Horas"]
                    
                    if not df_ed.equals(pd.DataFrame(st.session_state['lista_cargas'])):
                        st.session_state['lista_cargas'] = df_ed.to_dict('records')
                        st.rerun()

            with col_out:
                st.markdown("#### 2. Dimensionamento Automático")
                load_wh = sum(c['Total_Wh'] for c in st.session_state['lista_cargas'])
                load_w_pico = sum(c['Total_W'] for c in st.session_state['lista_cargas'])
                
                k1, k2 = st.columns(2)
                k1.metric("Consumo", f"{load_wh/1000:.2f} kWh")
                k2.metric("Pico de Carga", f"{load_w_pico} W")
                
                if load_wh > 0:
                    st.divider()
                    inv_db = st.session_state['inversores']
                    
                    # Smart Select
                    inv_candidatos = inv_db[inv_db['Potencia_kW'] * 1000 >= load_w_pico]
                    
                    aviso_sobrecarga = False
                    if inv_candidatos.empty:
                        idx_sugerido = len(inv_db) - 1
                        aviso_sobrecarga = True
                    else:
                        modelo_sugerido = inv_candidatos.iloc[0]['Modelo']
                        idx_sugerido = inv_db[inv_db['Modelo'] == modelo_sugerido].index[0]
                    
                    with st.container(border=True):
                        st.markdown("**Configuração Sugerida:**")
                        c_sel_1, c_sel_2 = st.columns(2)
                        inv_sel = c_sel_1.selectbox("Inversor", inv_db['Modelo'], index=int(idx_sugerido))
                        if aviso_sobrecarga and inv_sel == inv_db.iloc[-1]['Modelo']:
                                st.markdown(f"<div class='warning-box'>⚠️ Carga excede capacidade ({inv_sel})</div>", unsafe_allow_html=True)

                        r_inv = inv_db[inv_db['Modelo'] == inv_sel].iloc[0]
                        
                        bat_db = st.session_state['baterias']
                        bats_comp = bat_db[bat_db['Compatibilidade'] == r_inv['Compatibilidade']]
                        bat_sel = c_sel_2.selectbox("Bateria", bats_comp['Modelo'])
                        mod_sel = st.selectbox("Painel", st.session_state['modulos']['Modelo'])
                        auto = st.slider("Autonomia (Dias)", 0.5, 3.0, 1.0, 0.5)
                    
                    r_bat = bats_comp[bats_comp['Modelo'] == bat_sel].iloc[0]
                    r_mod = st.session_state['modulos'][st.session_state['modulos']['Modelo'] == mod_sel].iloc[0]
                    res = calcular_sistema(load_wh/1000, load_w_pico, auto, r_inv, r_bat, r_mod)
                    
                    st.info(f"✅ Sistema Híbrido **{r_inv['Compatibilidade']}** Dimensionado")
                    
                    tab_res1, tab_res2 = st.tabs(["📦 Lista de Materiais", "📊 Gráficos"])
                    
                    with tab_res1:
                        cr1, cr2 = st.columns(2)
                        with cr1:
                            st.markdown("**ESS (Baterias)**")
                            st.write(f"• **{res['qtd_bat']}x** {bat_sel}")
                            st.caption(f"Total: {res['banco_kwh']:.2f} kWh")
                            if res['qtd_pcu'] > 0:
                                st.write(f"• **{res['qtd_pcu']}x** PCU (Controlador)")
                                st.caption(res['msg_hv'])
                        with cr2:
                            st.markdown("**Gerador Solar**")
                            st.write(f"• **{res['qtd_mod']}x** {mod_sel}")
                            st.caption(f"Total: {res['gerador_kwp']:.2f} kWp")
                            st.write(f"• **1x** {inv_sel}")
                            st.caption(res['status_inv'])
                    
                    with tab_res2:
                        df_c = pd.DataFrame({
                            "Tipo": ["Consumo", "Solar", "Banco"],
                            "kWh": [load_wh/1000, res['gerador_kwp']*4.8, res['banco_kwh']],
                            "Cor": ["#e74c3c", "#f1c40f", "#2ecc71"]
                        })
                        st.plotly_chart(px.bar(df_c, x="Tipo", y="kWh", color="Tipo", color_discrete_sequence=df_c["Cor"]), use_container_width=True)

    # ABA 2: CLIENTES
    with tabs[1]:
        st.header("Gestão de Clientes")
        with st.form("cli_new", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nm = c1.text_input("Nome")
            cid = c2.text_input("Cidade/UF")
            tel = c3.text_input("Telefone")
            if st.form_submit_button("Salvar", type="primary"):
                if nm:
                    st.session_state['clientes'].append({"Nome": nm, "Cidade": cid, "Telefone": tel})
                    st.success("Salvo!")
                    st.rerun()
        if st.session_state['clientes']:
            st.dataframe(pd.DataFrame(st.session_state['clientes']), use_container_width=True)

    # ABA 3: EQUIPAMENTOS
    with tabs[2]:
        st.dataframe(st.session_state['inversores'])
        st.dataframe(st.session_state['baterias'])

    # ABA 4: BACKUP
    with tabs[3]:
        st.markdown("## 💾 Central de Dados")
        col_exp, col_imp = st.columns(2, gap="large")
        
        with col_exp:
            with st.container(border=True):
                st.markdown("### 📤 Exportar")
                st.info("Backup completo (.json) contendo clientes e projetos.")
                k1, k2 = st.columns(2)
                k1.metric("Clientes", len(st.session_state['clientes']))
                k2.metric("Itens Carga", len(st.session_state['lista_cargas']))
                json_data = gerar_backup()
                st.download_button("⬇️ Baixar JSON", json_data, f"backup_{st.session_state['projeto_id']}.json", "application/json", type="primary", use_container_width=True)

        with col_imp:
            with st.container(border=True):
                st.markdown("### 📥 Restaurar")
                st.warning("⚠️ Atenção: Substitui os dados atuais.")
                up = st.file_uploader("Arquivo JSON", type="json")
                if up and st.button("✅ Restaurar", use_container_width=True):
                    if carregar_backup(up): st.success("Restaurado!"); st.rerun()

    # ABA 5: ADMIN
    if st.session_state['is_admin']:
        with tabs[4]:
            st.header("Admin: Usuários do Sistema")
            st.write(carregar_usuarios_db())

# ==========================================
# 7. CÓDIGO DA APLICAÇÃO DE PROPOSTAS (Code B)
# ==========================================
def app_propostas():
    # --- CONSTANTES DO MÓDULO PROPOSTAS ---
    TAXA_FIXA_CARTAO = 2286.00
    CUSTO_CARENCIA_FINANC = 1350.00
    DEGRADACAO_PAINEL_ANUAL = 0.005 # 0.5% ao ano
    FIO_B_PERCENT_MAP = {2023: 15.0, 2024: 30.0, 2025: 45.0, 2026: 60.0, 2027: 75.0, 2028: 90.0}
    MINIMO_KWH_MAP = {"Monofásico": 30, "Bifásico": 50, "Trifásico": 100}
    
    # --- HELPER FUNCTIONS (PROPOSTAS) ---
    def format_currency_brl(valor: float) -> str:
        if valor is None: valor = 0.0
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def sync_slider_autoconsumo():
        if "slider_autoconsumo_view" in st.session_state:
            st.session_state.autoconsumo_val = st.session_state.slider_autoconsumo_view

    def calcular_tir_interna(fluxo_caixa: List[float]) -> float:
        try:
            rate = 0.1
            for _ in range(100):
                npv = 0
                npv_derivative = 0
                for t, val in enumerate(fluxo_caixa):
                    npv += val / ((1 + rate) ** t)
                    npv_derivative -= t * val / ((1 + rate) ** (t + 1))
                if abs(npv_derivative) < 1e-6: return 0.0
                new_rate = rate - npv / npv_derivative
                if abs(new_rate - rate) < 1e-6: return new_rate
                rate = new_rate
            return rate
        except: return 0.0

    def save_to_google_sheets(data: Dict[str, Any]):
        try:
            if "gcp_service_account" in st.secrets:
                creds = st.secrets["gcp_service_account"]
                sheet_id = st.secrets["google_sheet_id"]
                if gspread:
                    gc = gspread.service_account_from_dict(creds)
                    sh = gc.open_by_key(sheet_id).sheet1
                    fin = data.get("dados_cliente_fin", {})
                    row = [
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        data.get("cliente"), data.get("telefone"), data.get("email"),
                        data.get("tipo_conexao"), data.get("kwh_mensal"), data.get("taxa_iluminacao_publica"),
                        data.get("autoconsumo_percent"), data.get("kwp_total"), data.get("pot_painel_w"),
                        data.get("qtd_paineis"), format_currency_brl(data.get("valor_final")),
                        data.get("modalidade"), format_currency_brl(data.get("parcela_mensal")),
                        data.get("payback_str"), format_currency_brl(data.get("economia_mensal")),
                        format_currency_brl(data.get("nova_fatura_estimada")),
                        fin.get("cpf", fin.get("cnpj")), str(fin.get("data_nasc", fin.get("data_abertura"))),
                        fin.get("endereco"), fin.get("ramo", "")
                    ]
                    sh.append_row(row)
            else:
                print("AVISO: Secrets não encontrados (Modo Local).")
        except Exception as e:
            st.error(f"Erro ao salvar planilha: {e}")

    def dimensionar_sistema_func(kwh, hsp, perdas, pot_w, override=None):
        if kwh <= 0: return 0, 0.0, 0.0
        pot_kw = pot_w / 1000
        energia_painel = pot_kw * hsp * 30 * (1 - perdas)
        if energia_painel <= 0: return 0, 0.0, 0.0
        qtd_calc = kwh / energia_painel
        qtd_rec = max(1, math.ceil(qtd_calc))
        qtd = override if override and override > 0 else qtd_rec
        return qtd, qtd * pot_kw, qtd * energia_painel

    def calcular_fluxo_mensal_comparativo(meses_total, kwh_cons, tarifa, geracao, auto_pct, fio_b_pct, ano_ini, inflacao_anual, deg_anual, kwh_min, ilum, parcela_mensal, meses_parcela):
        inflacao_mes = (1 + inflacao_anual) ** (1/12) - 1
        deg_mes = (1 - deg_anual) ** (1/12) - 1
        auto_frac = auto_pct / 100
        dados_meses, gasto_old_list, desembolso_new_list = [], [], []
        
        for m in range(1, meses_total + 1):
            ano_rel = math.ceil(m / 12)
            ano_cal = ano_ini + (ano_rel - 1)
            perc_fio = FIO_B_PERCENT_MAP.get(ano_cal, 100.0) / 100
            fator_inf = (1 + inflacao_mes) ** (m - 1)
            tarifa_at = tarifa * fator_inf
            ilum_at = ilum * fator_inf
            geracao_at = geracao * ((1 - deg_mes) ** (m - 1))
            
            gasto_sem = (kwh_cons * tarifa_at) + ilum_at
            
            excedente = geracao_at * (1 - auto_frac)
            c_fio = excedente * (tarifa_at * (fio_b_pct/100)) * perc_fio
            c_disp = kwh_min * tarifa_at
            custo_rede = max(c_fio, c_disp)
            deficit = max(0, kwh_cons - geracao_at)
            c_deficit = deficit * tarifa_at
            
            nova_conta = custo_rede + ilum_at + c_deficit
            valor_parcela_atual = parcela_mensal if m <= meses_parcela else 0.0
            desembolso_total = nova_conta + valor_parcela_atual
            
            dados_meses.append(m)
            gasto_old_list.append(gasto_sem)
            desembolso_new_list.append(desembolso_total)
            
        return pd.DataFrame({
            "Mês": dados_meses,
            "Conta Antiga (Sem Solar)": gasto_old_list,
            "Desembolso Total (Com Solar)": desembolso_new_list
        })

    def calcular_fluxo_acumulado(anos, invest_inicial, kwh_cons, tarifa, geracao, auto_pct, fio_b_pct, ano_ini, inflacao, deg, kwh_min, ilum, parcela_mensal, meses_parcela):
        lista_anos = list(range(1, anos + 1))
        custo_acum_sem, custo_acum_com = [], []
        fluxo_liquido_tir = [-invest_inicial if invest_inicial > 0 else 0] 
        acc_sem = 0.0
        acc_com = invest_inicial if meses_parcela == 0 else 0.0
        auto_frac = auto_pct / 100

        for ano in lista_anos:
            ano_cal = ano_ini + (ano - 1)
            perc_fio = FIO_B_PERCENT_MAP.get(ano_cal, 100.0) / 100
            tarifa_inf = tarifa * ((1 + inflacao) ** (ano - 1))
            ilum_inf = ilum * ((1 + inflacao) ** (ano - 1))
            geracao_deg = geracao * ((1 - deg) ** (ano - 1))

            gasto_anual_sem = (kwh_cons * 12 * tarifa_inf) + (ilum_inf * 12)
            acc_sem += gasto_anual_sem
            custo_acum_sem.append(acc_sem)

            excedente = geracao_deg * (1 - auto_frac)
            c_fio = (excedente * (tarifa_inf * (fio_b_pct/100)) * perc_fio) * 12
            c_disp = (kwh_min * tarifa_inf) * 12
            custo_rede = max(c_fio, c_disp)
            deficit = max(0, (kwh_cons * 12) - (geracao_deg * 12))
            custo_deficit = deficit * tarifa_inf
            custo_operacional_anual = custo_rede + (ilum_inf * 12) + custo_deficit
            
            pagamento_parcelas_ano = 0.0
            if meses_parcela > 0:
                meses_neste_ano = max(0, min(12, meses_parcela - ((ano - 1) * 12)))
                pagamento_parcelas_ano = meses_neste_ano * parcela_mensal
            
            gasto_anual_com = custo_operacional_anual + pagamento_parcelas_ano
            acc_com += gasto_anual_com
            custo_acum_com.append(acc_com)
            fluxo_liquido_tir.append(gasto_anual_sem - gasto_anual_com)

        return pd.DataFrame({
            "Ano": lista_anos, 
            "Acumulado Sem Solar": custo_acum_sem,
            "Acumulado Com Solar": custo_acum_com
        }), fluxo_liquido_tir

    # --- UI FUNCTIONS (PROPOSTAS) ---
    def render_cabecalho():
        st.markdown(f"""
            <h1 style="text-align:center; color:{COR_PRIMARIA_PROP}; margin-bottom:0;">Brasil Enertech</h1>
            <h3 style="text-align:center; color:#444; margin-top:4px;">Gerador de Propostas</h3>
            <p style="text-align:center; color:#555;">
                Dimensione seu sistema de forma simples e prática.<br>
                Siga-nos: <a href="https://instagram.com/brasilenertech" target="_blank"><b>@brasilenertech</b></a>
            </p>
        """, unsafe_allow_html=True)
        st.markdown("---")

    def renderizar_entradas_cliente():
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            nome = c1.text_input("Nome do Cliente", "Cliente Exemplo")
            tel = c1.text_input("Telefone", "(82) 99999-9999")
            email = c2.text_input("E-mail", "email@exemplo.com")
            kwh = c2.number_input("Consumo (kWh/mês)", 50.0, value=800.0, step=10.0)
            tarifa = c3.number_input("Tarifa (R$/kWh)", 0.1, value=1.10, step=0.05)
            tipo = c3.selectbox("Tipo de Conexão", ["Monofásico", "Bifásico", "Trifásico"], 0)
            c4, c5 = st.columns(2)
            ilum = c4.number_input("Taxa Iluminação Pública (R$)", 0.0, value=30.0, step=5.0)
        return nome, tel, email, kwh, tarifa, tipo, ilum

    def renderizar_configuracoes_tecnicas():
        with st.container(border=True):
            st.subheader("Configurações Técnicas")
            c1, c2, c3, c4 = st.columns(4)
            hsp = c1.number_input("HSP (h/dia)", 3.0, 7.0, 5.0, 0.1)
            perdas = c2.number_input("Perdas Globais (%)", 5.0, 30.0, 15.0, 1.0)
            pot = c3.selectbox("Potência Módulo (W)", [585, 605, 650, 700], 2)
            valor_kwp = c4.number_input("Valor do kWp (R$)", 1500.0, 5000.0, 2200.0, 50.0)
            c5, c6, c7 = st.columns(3)
            c5.selectbox("Concessionária", ["Equatorial - AL", "Outra"])
            fio_b = c6.number_input("Fração Fio B da Tarifa (%)", 10.0, 50.0, 28.0, 1.0)
            ano_atual = datetime.datetime.now().year
            ano_ini = c7.selectbox("Ano de Conexão", list(range(ano_atual, 2030)), 0)
        return hsp, perdas, pot, valor_kwp, fio_b, ano_ini

    def renderizar_dimensionamento(kwh, hsp, perdas, pot, valor_kwp):
        with st.container(border=True):
            st.subheader("Dimensionamento do Sistema")
            qtd_rec, _, _ = dimensionar_sistema_func(kwh, hsp, perdas/100, pot)
            if "qtd_paineis" not in st.session_state: st.session_state.qtd_paineis = qtd_rec
            
            c_btns, c_txt = st.columns([1, 1])
            with c_btns:
                b1, b2, b3 = st.columns(3)
                if b1.button("➖", use_container_width=True): 
                    if st.session_state.qtd_paineis > 1: st.session_state.qtd_paineis -= 1; st.rerun()
                if b2.button("➕", use_container_width=True): 
                    st.session_state.qtd_paineis += 1; st.rerun()
                if b3.button("Reset", use_container_width=True): 
                    st.session_state.qtd_paineis = qtd_rec; st.rerun()
            with c_txt:
                 st.markdown(f"<div style='margin-top: -8px;'>**Qtd. atual: {st.session_state.qtd_paineis} painéis**<br><small>(Recomendado: {qtd_rec})</small></div>", unsafe_allow_html=True)

            qtd_fin, kwp, geracao = dimensionar_sistema_func(kwh, hsp, perdas/100, pot, st.session_state.qtd_paineis)
            total = kwp * valor_kwp
            st.markdown("---")
            d1, d2, d3 = st.columns(3)
            d1.metric("Potência Total", f"{kwp:.2f} kWp")
            d2.metric("Geração Mensal", f"{geracao:,.0f} kWh")
            d3.metric("Valor Base", format_currency_brl(total))
        return qtd_fin, kwp, geracao, total

    def renderizar_simulacao_economia(geracao, tarifa, fio_b_pct, ano_ini, kwh_cons, kwh_min, ilum):
        with st.container(border=True):
            st.subheader("Simulação de Economia (Ano 1)")
            if "autoconsumo_val" not in st.session_state: st.session_state.autoconsumo_val = 40
            st.slider("Autoconsumo Instantâneo (%)", 10, 100, key="slider_autoconsumo_view", on_change=sync_slider_autoconsumo, help="Quanto maior, menos você paga de Fio B.")
            auto_pct = st.session_state.autoconsumo_val
            
            perc_fio = FIO_B_PERCENT_MAP.get(ano_ini, 100.0) / 100
            gasto_antigo = (kwh_cons * tarifa) + ilum
            excedente = geracao * (1 - auto_pct/100)
            c_fio = excedente * (tarifa * (fio_b_pct/100)) * perc_fio
            c_disp = kwh_min * tarifa
            custo_rede = max(c_fio, c_disp)
            pagando_fio_b = c_fio > c_disp
            gasto_novo = custo_rede + ilum
            
            economia_mensal = max(0, gasto_antigo - gasto_novo)
            economia_anual = economia_mensal * 12
            reducao_pct = (1 - (gasto_novo / gasto_antigo)) * 100 if gasto_antigo > 0 else 0

            fig = go.Figure(data=[
                go.Bar(name='Antes (Sem Solar)', x=['Conta de Luz'], y=[gasto_antigo], marker_color=COR_VERMELHO_PROP, text=format_currency_brl(gasto_antigo), textposition='auto'),
                go.Bar(name='Depois (Com Solar)', x=['Conta de Luz'], y=[gasto_novo], marker_color=COR_PRIMARIA_PROP, text=format_currency_brl(gasto_novo), textposition='auto')
            ])
            fig.update_layout(title="Comparativo Mensal: Antes vs. Depois", yaxis_title="Valor (R$)", barmode='group', height=300, margin=dict(l=20, r=20, t=40, b=20), template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Economia Mensal", format_currency_brl(economia_mensal))
            c2.metric("💰 Economia Anual", format_currency_brl(economia_anual))
            c3.metric("📉 Redução na Conta", f"{reducao_pct:.1f}%")
            st.markdown("---")

            st.markdown("##### 🔍 Detalhamento da Nova Fatura")
            c4, c5, c6 = st.columns(3)
            c4.metric("Custo Fio B", format_currency_brl(c_fio), delta_color="off")
            c5.metric("Custo Disponibilidade", format_currency_brl(c_disp), delta_color="off")
            c6.metric("Iluminação Pública", format_currency_brl(ilum), delta_color="off")
            
            with st.expander("📊 Ver Balanço Energético (kWh)"):
                df_balanco = pd.DataFrame({
                    "Descrição": ["Geração Total", "Consumo Instantâneo (Autoconsumo)", "Injetado na Rede (Crédito)", "Consumo da Rede (Abatido)"],
                    "Energia (kWh)": [f"{geracao:.0f}", f"{geracao * (auto_pct/100):.0f}", f"{excedente:.0f}", f"{kwh_cons - (geracao * (auto_pct/100)):.0f}"]
                })
                st.table(df_balanco)

            with st.expander("📚 Entenda por que sua conta não zerou (Raio-X)"):
                st.markdown(f"""
                Mesmo gerando sua própria energia, existem custos regulatórios:
                1. **Iluminação Pública:** R$ {ilum:,.2f}.
                2. **Custo da Rede:** Pela Lei 14.300, você paga o **MAIOR** valor entre o **Fio B** e a **Taxa Mínima**.
                """)
                if pagando_fio_b:
                    st.info(f"💡 **Você paga o Fio B:** O custo pelo uso da rede (R$ {c_fio:,.2f}) superou a taxa mínima.")
                else:
                    st.info(f"💡 **Você paga a Taxa Mínima:** O Fio B foi baixo, então vale a taxa mínima (R$ {c_disp:,.2f}).")
                
        return economia_mensal, gasto_novo, c_fio, c_disp, auto_pct

    def renderizar_pagamento(valor_base, economia_mes):
        with st.container(border=True):
            st.subheader("Simulação de Pagamento")
            forma = st.selectbox("Forma de pagamento", ["À vista (5% desconto)", "Financiamento", "Cartão de crédito"])
            valor_final = valor_base
            parcela = 0.0
            meses_pag = 0
            fin_data = {}

            if "Vista" in forma:
                valor_final = valor_base * 0.95
                st.success(f"**Valor Final:** {format_currency_brl(valor_final)}")
            
            elif "Financiamento" in forma:
                st.info("ℹ️ Preencha para análise.")
                tipo = st.radio("Cliente", ["PF", "PJ"], horizontal=True, key="tipo_cli_fin")
                c1, c2 = st.columns(2)
                if tipo == "PF":
                    doc = c1.text_input("CPF", key="fin_doc"); dt = c2.date_input("Nascimento"); end = st.text_input("Endereço", key="fin_end")
                    fin_data = {"doc": doc, "data": str(dt), "end": end, "tipo": "PF"}
                else:
                    doc = c1.text_input("CNPJ", key="fin_doc"); dt = c2.date_input("Abertura"); end = st.text_input("Endereço", key="fin_end"); ramo = st.text_input("Ramo", key="fin_ramo")
                    fin_data = {"doc": doc, "data": str(dt), "end": end, "ramo": ramo, "tipo": "PJ"}
                st.markdown("---")
                c3, c4, c5 = st.columns(3)
                meses_pag = c3.selectbox("Parcelas", [36, 48, 60, 72], 1)
                carencia = c4.selectbox("Carência", [0, 1, 2, 3])
                taxa = c5.slider("Taxa a.m. (%)", 1.2, 2.8, 1.5, 0.1) / 100
                v_fin = valor_base + (carencia * CUSTO_CARENCIA_FINANC)
                parcela = (v_fin * taxa) / (1 - (1 + taxa) ** (-meses_pag)) if taxa > 0 else v_fin / meses_pag
                valor_final = parcela * meses_pag
                st.success(f"**Parcela:** {format_currency_brl(parcela)}")
                
            elif "Cartão" in forma:
                c1, c2 = st.columns(2)
                meses_pag = c1.selectbox("Vezes", list(range(1, 22)), 11)
                taxa = c2.number_input("Taxa a.m.", 0.5, 3.0, 1.25, 0.05) / 100
                v_cartao = valor_base + TAXA_FIXA_CARTAO
                parcela = (v_cartao * taxa) / (1 - (1 + taxa) ** (-meses_pag)) if taxa > 0 else v_cartao / meses_pag
                valor_final = parcela * meses_pag
                st.success(f"**Parcela:** {format_currency_brl(parcela)}")

            if parcela > 0:
                balanco = economia_mes - parcela
                c1, c2, c3 = st.columns(3)
                c1.metric("Economia", format_currency_brl(economia_mes))
                c2.metric("Parcela", format_currency_brl(parcela))
                c3.metric("Saldo", format_currency_brl(balanco), delta_color="normal" if balanco > 0 else "inverse")

        return forma, valor_final, parcela, fin_data, meses_pag

    def renderizar_projecao_financeira(invest, kwh_cons, tarifa, geracao, auto_pct, fio_b, ano_ini, kwh_min, ilum, parcela_mensal, meses_parcela):
        with st.container(border=True):
            tipo_grafico = st.radio("Modo de Visualização:", ["📅 Fluxo Mensal (Troca de Bolso)", "📈 Retorno Acumulado (25 Anos)"], horizontal=True)
            st.markdown("---")
            inflacao_val = st.slider("Inflação Energética Anual (%)", 3.0, 10.0, 5.0, 0.5, key="inf_sl_proj") / 100
            
            if "Mensal" in tipo_grafico:
                st.info("ℹ️ **Entenda o Gráfico:** Se a linha **Verde** (Nova Conta + Parcela) estiver abaixo da **Vermelha** (Conta Antiga), significa que você já começa economizando dinheiro todo mês.")
                meses_view = max(12, meses_parcela) if meses_parcela > 0 else 24
                df_mes = calcular_fluxo_mensal_comparativo(meses_view, kwh_cons, tarifa, geracao, auto_pct, fio_b, ano_ini, inflacao_val, DEGRADACAO_PAINEL_ANUAL, kwh_min, ilum, parcela_mensal, meses_parcela)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_mes["Mês"], y=df_mes["Conta Antiga (Sem Solar)"], name="Conta Antiga", line=dict(color=COR_VERMELHO_PROP, width=3, dash="dot"), fill='tozeroy', fillcolor='rgba(217, 83, 79, 0.1)'))
                fig.add_trace(go.Scatter(x=df_mes["Mês"], y=df_mes["Desembolso Total (Com Solar)"], name="Nova Conta + Parcela", line=dict(color=COR_PRIMARIA_PROP, width=4), fill='tozeroy', fillcolor='rgba(58, 111, 28, 0.2)'))
                fig.update_layout(title="Desembolso Acumulado Mês a Mês", xaxis_title="Meses", yaxis_title="R$ Acumulado", template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig, use_container_width=True)
                return "+ 25 anos", 0.0, "N/A"

            else:
                st.info("ℹ️ **Entenda o Gráfico:** A longo prazo, a área **Vermelha** representa todo o dinheiro perdido com aluguel de energia. A área **Verde** é o custo do seu investimento.")
                invest_inicial = invest if meses_parcela == 0 else 0
                df, fluxo_tir = calcular_fluxo_acumulado(25, invest_inicial, kwh_cons, tarifa, geracao, auto_pct, fio_b, ano_ini, inflacao_val, DEGRADACAO_PAINEL_ANUAL, kwh_min, ilum, parcela_mensal, meses_parcela)
                
                tir_val = calcular_tir_interna(fluxo_tir) * 100
                tir_str = f"{tir_val:.1f}% a.a." if tir_val > 0 else "N/A"
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["Ano"], y=df["Acumulado Sem Solar"], name="Gasto Sem Solar", line=dict(color=COR_VERMELHO_PROP, width=3, dash="dot"), fill='tozeroy', fillcolor='rgba(217, 83, 79, 0.1)'))
                fig.add_trace(go.Scatter(x=df["Ano"], y=df["Acumulado Com Solar"], name="Custo Com Solar", line=dict(color=COR_PRIMARIA_PROP, width=4), fill='tozeroy', fillcolor='rgba(58, 111, 28, 0.2)'))
                
                payback_msg = "+ 25 anos"; econom_total = df["Acumulado Sem Solar"].iloc[-1] - df["Acumulado Com Solar"].iloc[-1]
                try:
                    cross = df[df["Acumulado Com Solar"] <= df["Acumulado Sem Solar"]]
                    if not cross.empty:
                        ano_pb = cross["Ano"].iloc[0]
                        payback_msg = "Imediato" if ano_pb == 1 else f"~ {ano_pb} anos"
                except: pass

                fig.update_layout(title="Gasto Acumulado Total (R$)", xaxis_title="Anos", yaxis_title="Acumulado (R$)", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"<div class='metric-custom' style='text-align:center'><h4>Total Pago</h4><h3>{format_currency_brl(df['Acumulado Com Solar'].iloc[meses_parcela//12] if meses_parcela else invest)}</h3></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-custom' style='text-align:center'><h4>Payback</h4><h3>{payback_msg}</h3></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-custom' style='text-align:center'><h4>TIR</h4><h3>{tir_str}</h3></div>", unsafe_allow_html=True)
                c4.markdown(f"<div class='metric-custom' style='text-align:center'><h4>Lucro Total</h4><h3>{format_currency_brl(econom_total)}</h3></div>", unsafe_allow_html=True)

                return payback_msg, econom_total, tir_str

    def renderizar_exportar_proposta(dados):
        with st.container(border=True):
            st.subheader("Finalizar Proposta")
            valido = True
            msg = ""
            if dados["modalidade"] == "Financiamento":
                fin = dados["dados_cliente_fin"]
                if not fin.get("doc") or not fin.get("end"): valido = False; msg = "⚠️ Preencha Documento e Endereço na aba Pagamento."

            nova_fat = dados.get("nova_fatura_estimada", 0)
            txt_zap = f"""
            *Simulação Brasil Enertech* ☀️
            ---------------------------
            👤 {dados['cliente']}
            📍 {dados['tipo_conexao']} | {dados['kwh_mensal']} kWh
            
            ⚡ Sistema: {dados['kwp_total']:.2f} kWp ({dados['qtd_paineis']}x {dados['pot_painel_w']}W)
            💰 Investimento: {format_currency_brl(dados['valor_final'])} ({dados['modalidade']})
            📉 Economia Mês: {format_currency_brl(dados['economia_mensal'])}
            🧾 Nova Fatura: {format_currency_brl(nova_fat)}
            🔄 Payback: {dados['payback_str']}
            📈 TIR: {dados.get('tir_str', 'N/A')}
            """
            if "dados_cliente_fin" in dados and dados["dados_cliente_fin"]: txt_zap += f"\n📋 Dados Análise: {dados['dados_cliente_fin']}"
            link = f"https://wa.me/5582998098501?text={quote(txt_zap)}"
            
            if not valido: st.warning(msg); st.button("✅ Solicitar Visita Técnica", disabled=True, use_container_width=True)
            else:
                if st.button("✅ Solicitar Visita Técnica pelo WhatsApp", type="primary", use_container_width=True):
                    save_to_google_sheets(dados)
                    st.success("Enviando..."); components.html(f'<meta http-equiv="refresh" content="1; url={link}">', height=0)

    # --- MAIN LOGIC (PROPOSTAS) ---
    render_cabecalho()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["1️⃣ Início", "2️⃣ Dimensionamento", "3️⃣ Simulação", "4️⃣ Projeção & Pagamento", "5️⃣ Enviar"])
    
    with tab1:
        st.subheader("Passo 1: Dados do Cliente")
        inputs_cli = renderizar_entradas_cliente() 
        kwh_min = MINIMO_KWH_MAP.get(inputs_cli[5], 100)
        st.markdown("---")
        st.subheader("Passo 2: Configurações Técnicas")
        inputs_tec = renderizar_configuracoes_tecnicas() 
    
    with tab2:
        res_dim = renderizar_dimensionamento(inputs_cli[3], inputs_tec[0], inputs_tec[1], inputs_tec[2], inputs_tec[3])
    
    with tab3:
        res_sim = renderizar_simulacao_economia(res_dim[2], inputs_cli[4], inputs_tec[4], inputs_tec[5], inputs_cli[3], kwh_min, inputs_cli[6])
    
    with tab4:
        res_pag = renderizar_pagamento(res_dim[3], res_sim[0]) 
        st.markdown("---")
        res_proj = renderizar_projecao_financeira(
            res_pag[1], inputs_cli[3], inputs_cli[4], res_dim[2], res_sim[4], 
            inputs_tec[4], inputs_tec[5], kwh_min, inputs_cli[6], 
            res_pag[2], res_pag[4]
        )
        
    with tab5:
        dados = {
            "cliente": inputs_cli[0], "telefone": inputs_cli[1], "email": inputs_cli[2],
            "kwh_mensal": inputs_cli[3], "tipo_conexao": inputs_cli[5], "taxa_iluminacao_publica": inputs_cli[6],
            "kwp_total": res_dim[1], "qtd_paineis": res_dim[0], "pot_painel_w": inputs_tec[2],
            "valor_final": res_pag[1], "modalidade": res_pag[0], "parcela_mensal": res_pag[2],
            "economia_mensal": res_sim[0], "nova_fatura_estimada": res_sim[1], "autoconsumo_percent": res_sim[4],
            "payback_str": res_proj[0], "economia_25_anos": res_proj[1], "tir_str": res_proj[2],
            "dados_cliente_fin": res_pag[3]
        }
        renderizar_exportar_proposta(dados)

# ==========================================
# 8. ROTEADOR DE APPS
# ==========================================
if app_mode == "🔋 Dimensionamento Baterias":
    app_baterias()
    
elif app_mode == "☀️ Gerador de Propostas":
    # CORREÇÃO: Removemos as colunas de centralização (c_vazio1, c_conteudo...)
    # para evitar o erro de "Nested Columns" (Colunas dentro de Colunas).
    # O sistema agora ocupará a largura total da tela, mantendo todas as funções ativas.
    
    # Container para dar um leve respiro nas laterais se estiver muito largo
    with st.container():
        st.markdown("<div style='margin: 0 auto; max-width: 100%;'>", unsafe_allow_html=True)
        app_propostas()
        st.markdown("</div>", unsafe_allow_html=True)
