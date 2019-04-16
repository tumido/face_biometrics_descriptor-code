from distutils.core import setup  # noqa

setup(
    name='capsnet',
    description='CapsNet - face recognition',
    version='0.1',
    author='Tomas Coufal',
    packages=['capsnet',],
    license='Apache 2.0',
    install_requires=['tensorflow', 'scikit-learn', 'keras', 'numpy']
)