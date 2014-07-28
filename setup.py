from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages = [], excludes = [])

executables = [
    Executable('TheRNG.py')
]

setup(name='The RNG',
      version = '1.0',
      description = 'A game in which the player(s) dodge increasingly numerous numbers.',
      options = dict(build_exe = buildOptions),
      executables = executables)
