import streamlit as st
import requests

# FastAPI Backend URL
BASE_URL = "http://127.0.0.1:8000"

# Session State for Token Storage
if "token" not in st.session_state:
    st.session_state.token = None

st.title(" Banking App")

# --- Register User ---
st.subheader("🔑 Register")
username = st.text_input("Username", key="register_username")
password = st.text_input("Password", type="password", key="register_password")
if st.button("Register"):
    response = requests.post(f"{BASE_URL}/register", json={"username": username, "password": password})
    st.success(response.json().get("message", "Error"))

# --- Sign In ---
st.subheader(" Sign In")
login_username = st.text_input("Username", key="login_username")
login_password = st.text_input("Password", type="password", key="login_password")
if st.button("Login"):
    response = requests.post(f"{BASE_URL}/signin", json={"username": login_username, "password": login_password})
    if response.status_code == 200:
        st.session_state.token = response.json()["token"]
        st.success("Login Successful!")
    else:
        st.error(response.json().get("detail", "Login Failed"))

# --- Deposit Money ---
if st.session_state.token:
    st.subheader(" Deposit Money")
    deposit_amount = st.number_input("Amount", min_value=0.01)
    if st.button("Deposit"):
        headers = {"token": st.session_state.token}
        response = requests.post(f"{BASE_URL}/deposit", json={"amount": deposit_amount}, headers=headers)
        st.success(response.json().get("message", "Deposit Failed"))


# --- Withdraw Money ---
if st.session_state.token:
    st.subheader(" Withdraw Money")
    withdraw_amount = st.number_input("Amount", min_value=0.01, key="withdraw_amount")
    if st.button("Withdraw"):
        headers = {"token": st.session_state.token}
        response = requests.post(f"{BASE_URL}/withdraw", json={"amount": withdraw_amount}, headers=headers)
        if response.status_code == 200:
            st.success(response.json().get("message", "Withdrawal Failed"))
        else:
            st.error(response.json().get("detail", "Withdrawal Failed"))

# --- Get Balance ---
if st.session_state.token:
    st.subheader(" Account Balance")
    if st.button("Check Balance"):
        headers = {"token": st.session_state.token}
        response = requests.get(f"{BASE_URL}/balance", headers=headers)
        st.info(f"Current Balance: ${response.json().get('balance', 0)}")
