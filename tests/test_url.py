import os

import pytest
from PIL import Image, UnidentifiedImageError

from term_image.exceptions import URLNotFoundError
from term_image.image import ImageSource, TermImage

python_image = "tests/images/python.png"
python_url = (
    "https://raw.githubusercontent.com/AnonymouX47/term-image/main/tests/"
    "images/python.png"
)
python_img = Image.open(python_image)


def test_from_url():
    with pytest.raises(TypeError, match=r".* a string .*"):
        TermImage.from_url(python_img)
    with pytest.raises(ValueError, match="Invalid URL.*"):
        TermImage.from_url(python_image)
    with pytest.raises(URLNotFoundError):
        TermImage.from_url(python_url + "e")
    with pytest.raises(UnidentifiedImageError):
        TermImage.from_url(
            "https://raw.githubusercontent.com/AnonymouX47/term-image/main/LICENSE"
        )

    image = TermImage.from_url(python_url)
    assert isinstance(image, TermImage)
    assert image._url == python_url
    assert os.path.exists(image._source)
    assert image._source_type is ImageSource.URL

    # Ensure size arguments get through
    with pytest.raises(ValueError, match=r".* both width and height"):
        TermImage.from_url(python_url, width=1, height=1)

    # Ensure scale argument gets through
    with pytest.raises(TypeError, match=r"'scale' .*"):
        TermImage.from_url(python_url, scale=1.0)


def test_source():
    image = TermImage.from_url(python_url)
    assert image.source == image._url == python_url
    assert image.source_type is ImageSource.URL


def test_close():
    image = TermImage.from_url(python_url)
    source = image._source

    image.close()
    assert not os.path.exists(source)
    with pytest.raises(AttributeError):
        image._url
