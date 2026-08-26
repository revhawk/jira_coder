"""
Demo 10: Basic Calculator
Simple calculator with just arithmetic operations (no memory, no binary mode)
"""
import streamlit as st

# Initialize session state
if 'display' not in st.session_state:
    st.session_state.display = '0'

# Title
st.title('Basic Calculator')

# Display
st.markdown(f'### Display: `{st.session_state.display}`')

# Create button grid layout
col1, col2, col3, col4 = st.columns(4)

# First row
with col1:
    if st.button('7', key='7', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '7'
        else:
            st.session_state.display += '7'
        st.rerun()

with col2:
    if st.button('8', key='8', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '8'
        else:
            st.session_state.display += '8'
        st.rerun()

with col3:
    if st.button('9', key='9', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '9'
        else:
            st.session_state.display += '9'
        st.rerun()

with col4:
    if st.button('➕', key='+', use_container_width=True):
        st.session_state.display += '+'
        st.rerun()

# Second row
with col1:
    if st.button('4', key='4', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '4'
        else:
            st.session_state.display += '4'
        st.rerun()

with col2:
    if st.button('5', key='5', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '5'
        else:
            st.session_state.display += '5'
        st.rerun()

with col3:
    if st.button('6', key='6', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '6'
        else:
            st.session_state.display += '6'
        st.rerun()

with col4:
    if st.button('➖', key='-', use_container_width=True):
        st.session_state.display += '-'
        st.rerun()

# Third row
with col1:
    if st.button('1', key='1', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '1'
        else:
            st.session_state.display += '1'
        st.rerun()

with col2:
    if st.button('2', key='2', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '2'
        else:
            st.session_state.display += '2'
        st.rerun()

with col3:
    if st.button('3', key='3', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '3'
        else:
            st.session_state.display += '3'
        st.rerun()

with col4:
    if st.button('✖️', key='*', use_container_width=True):
        st.session_state.display += '*'
        st.rerun()

# Fourth row
with col1:
    if st.button('0', key='0', use_container_width=True):
        if st.session_state.display != '0':
            st.session_state.display += '0'
        st.rerun()

with col2:
    if st.button('.', key='.', use_container_width=True):
        if '.' not in st.session_state.display.split()[-1]:
            st.session_state.display += '.'
        st.rerun()

with col3:
    if st.button('=', key='=', use_container_width=True):
        try:
            st.session_state.display = str(eval(st.session_state.display))
        except ZeroDivisionError:
            st.session_state.display = 'Error'
        except Exception:
            st.session_state.display = 'Error'
        st.rerun()

with col4:
    if st.button('➗', key='/', use_container_width=True):
        st.session_state.display += '/'
        st.rerun()

# Clear button
if st.button('Clear', key='C', use_container_width=True):
    st.session_state.display = '0'
    st.rerun()
