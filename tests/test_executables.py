import pkg_resources
import subprocess


def test_specfit():
    executable = pkg_resources.resource_filename('ifscube', '../bin/specfit')
    config = pkg_resources.resource_filename('ifscube', 'examples/halpha_gauss.cfg')
    input_data = pkg_resources.resource_filename('ifscube', 'examples/manga_onedspec.fits')
    subprocess.run([executable, '-o', '-c', config, input_data])
    assert 1


def test_cubefit():
    executable = pkg_resources.resource_filename('ifscube', '../bin/cubefit')
    config = pkg_resources.resource_filename('ifscube', 'examples/halpha_cube.cfg')
    input_data = pkg_resources.resource_filename('ifscube', 'examples/ngc3081_cube.fits')
    subprocess.run([executable, '-o', '-c', config, input_data])
    assert 1
