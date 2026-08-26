"""
Demo 12: Calculator with Binary Mode

Features:
- Button grid calculator
- Memory functions (M+, MR, MC)
- Binary mode (DEC/BIN toggle)
- Binary arithmetic (1000 + 10 = 1010)
"""
import streamlit as st
import re

# Helper functions (inline to avoid module dependency)
def square_root(a: float) -> float:
    """Returns the square root of a number."""
    import math
    if a < 0:
        raise ValueError("Cannot calculate square root of negative number")
    return math.sqrt(a)

# Initialize session state
if 'display' not in st.session_state:
    st.session_state.display = '0'
if 'memory' not in st.session_state:
    st.session_state.memory = 0
if 'mode' not in st.session_state:
    st.session_state.mode = 'DEC'  # DEC or BIN

# Title
st.title('Calculator with Binary Mode')

# Mode toggle
mode_col1, mode_col2 = st.columns(2)
with mode_col1:
    if st.button('DEC', key='mode_dec', use_container_width=True, type='primary' if st.session_state.mode == 'DEC' else 'secondary'):
        st.session_state.mode = 'DEC'
        # Convert binary display to decimal
        if st.session_state.display != '0' and st.session_state.display != 'Error':
            try:
                st.session_state.display = str(int(st.session_state.display, 2))
            except:
                pass
        st.rerun()

with mode_col2:
    if st.button('BIN', key='mode_bin', use_container_width=True, type='primary' if st.session_state.mode == 'BIN' else 'secondary'):
        st.session_state.mode = 'BIN'
        # Convert decimal display to binary
        if st.session_state.display != '0' and st.session_state.display != 'Error':
            try:
                st.session_state.display = bin(int(eval(st.session_state.display)))[2:]
            except:
                pass
        st.rerun()

# Display
st.markdown(f'### Display: `{st.session_state.display}` ({st.session_state.mode})')

# Create button grid layout
col1, col2, col3, col4 = st.columns(4)

# First row of buttons
with col1:
    if st.button('7', key='7', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '7'
        else:
            st.session_state.display += '7'
        st.rerun()

with col2:
    if st.button('8', key='8', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '8'
        else:
            st.session_state.display += '8'
        st.rerun()

with col3:
    if st.button('9', key='9', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '9'
        else:
            st.session_state.display += '9'
        st.rerun()

with col4:
    if st.button('➕', key='+', use_container_width=True):
        st.session_state.display += '+'
        st.rerun()

# Second row of buttons
with col1:
    if st.button('4', key='4', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '4'
        else:
            st.session_state.display += '4'
        st.rerun()

with col2:
    if st.button('5', key='5', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '5'
        else:
            st.session_state.display += '5'
        st.rerun()

with col3:
    if st.button('6', key='6', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '6'
        else:
            st.session_state.display += '6'
        st.rerun()

with col4:
    if st.button('➖', key='-', use_container_width=True):
        st.session_state.display += '-'
        st.rerun()

# Third row of buttons
with col1:
    if st.button('1', key='1', use_container_width=True):
        if st.session_state.display == '0':
            st.session_state.display = '1'
        else:
            st.session_state.display += '1'
        st.rerun()

with col2:
    if st.button('2', key='2', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '2'
        else:
            st.session_state.display += '2'
        st.rerun()

with col3:
    if st.button('3', key='3', use_container_width=True, disabled=(st.session_state.mode == 'BIN')):
        if st.session_state.display == '0':
            st.session_state.display = '3'
        else:
            st.session_state.display += '3'
        st.rerun()

with col4:
    if st.button('✖️', key='*', use_container_width=True):
        st.session_state.display += '*'
        st.rerun()

# Fourth row of buttons
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
            if st.session_state.mode == 'BIN':
                # Parse binary expression and evaluate
                expr = st.session_state.display
                # Replace binary numbers with decimal for eval
                def bin_to_dec(match):
                    return str(int(match.group(0), 2))
                # Match binary numbers (sequences of 0s and 1s)
                expr_dec = re.sub(r'[01]+', bin_to_dec, expr)
                result = eval(expr_dec)
                st.session_state.display = bin(int(result))[2:]
            else:
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

# Fifth row - Clear, Square Root
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button('Clear', key='C', use_container_width=True):
        st.session_state.display = '0'
        st.rerun()

with col2:
    if st.button('√', key='sqrt', use_container_width=True):
        try:
            if st.session_state.mode == 'BIN':
                # Convert binary to decimal, sqrt, back to binary
                dec_val = int(st.session_state.display, 2)
                result = square_root(float(dec_val))
                st.session_state.display = bin(int(result))[2:]
            else:
                result = square_root(float(eval(st.session_state.display)))
                st.session_state.display = str(result)
        except ValueError:
            st.session_state.display = 'Error'
        except Exception:
            st.session_state.display = 'Error'
        st.rerun()

# Memory Buttons Row
st.markdown('---')
mem_col1, mem_col2, mem_col3, mem_col4 = st.columns(4)

with mem_col1:
    if st.button('M+', key='M+', use_container_width=True):
        try:
            st.session_state.memory += float(eval(st.session_state.display))
            st.session_state.display = '0'
        except:
            pass
        st.rerun()

with mem_col2:
    if st.button('MR', key='MR', use_container_width=True):
        mem_value = str(st.session_state.memory)
        if st.session_state.display == '0':
            st.session_state.display = mem_value
        else:
            st.session_state.display += mem_value
        st.rerun()

with mem_col3:
    if st.button('MC', key='MC', use_container_width=True):
        st.session_state.memory = 0
        st.rerun()

with mem_col4:
    st.markdown(f'**Memory:** `{st.session_state.memory}`')
