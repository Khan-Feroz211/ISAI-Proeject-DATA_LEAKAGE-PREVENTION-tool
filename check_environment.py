import sys
import os

try:
    import google.colab
    print('🚀 You are in GOOGLE COLAB')
    print('   Files are in the cloud, not on local disk')
    
    # Show Colab-specific info
    print(f'\n📁 Current directory: {os.getcwd()}')
    
except ImportError:
    print('💻 You are in LOCAL environment')
    print('   Files are on your local disk')
    print(f'\n📁 Current directory: {os.getcwd()}')
