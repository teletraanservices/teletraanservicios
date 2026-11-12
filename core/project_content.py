import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from django.conf import settings


PROJECTS_FILE = settings.BASE_DIR / 'content' / 'projects.json'
STATIC_SOURCE_DIR = settings.BASE_DIR / 'core' / 'static'
PROJECT_MEDIA_PREFIX = PurePosixPath('core/media/projects')
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.webm'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 25 * 1024 * 1024


def _validate_media_path(value, extensions, max_size, static_source_dir):
    if not isinstance(value, str) or not value:
        raise ValueError('La ruta de archivo del proyecto debe ser texto.')
    relative_path = PurePosixPath(value)
    if (
        relative_path.is_absolute()
        or '..' in relative_path.parts
        or '\\' in value
        or relative_path.parts[:len(PROJECT_MEDIA_PREFIX.parts)] != PROJECT_MEDIA_PREFIX.parts
        or relative_path.suffix.lower() not in extensions
    ):
        raise ValueError(f'Ruta de archivo no permitida: {value}')

    media_path = static_source_dir.joinpath(*relative_path.parts)
    if not media_path.resolve().is_relative_to(static_source_dir.resolve()) or not media_path.is_file():
        raise ValueError(f'No existe el archivo del proyecto: {value}')
    if media_path.stat().st_size > max_size:
        raise ValueError(f'El archivo supera el límite permitido: {value}')
    return value


def _validate_https_url(value, label):
    if value in (None, ''):
        return ''
    if not isinstance(value, str):
        raise ValueError(f'{label} debe ser una URL.')
    parsed_url = urlparse(value)
    if parsed_url.scheme != 'https' or not parsed_url.netloc:
        raise ValueError(f'{label} debe comenzar con https://.')
    return value


def load_projects(projects_file=None, static_source_dir=None):
    projects_file = Path(projects_file or PROJECTS_FILE)
    static_source_dir = Path(static_source_dir or STATIC_SOURCE_DIR)
    with Path(projects_file).open(encoding='utf-8') as project_file:
        projects = json.load(project_file)
    if not isinstance(projects, list):
        raise ValueError('content/projects.json debe contener una lista de proyectos.')

    published_projects = []
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise ValueError(f'El proyecto en la posición {index} debe ser un objeto.')
        title = project.get('title')
        description = project.get('description')
        if not isinstance(title, str) or not title.strip() or len(title) > 120:
            raise ValueError(f'El proyecto en la posición {index} necesita un título de hasta 120 caracteres.')
        if not isinstance(description, str) or not description.strip() or len(description) > 1200:
            raise ValueError(f'El proyecto "{title}" necesita una descripción de hasta 1200 caracteres.')

        image = project.get('image', '')
        video_file = project.get('video_file', '')
        if image:
            _validate_media_path(image, IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, static_source_dir)
        if video_file:
            _validate_media_path(video_file, VIDEO_EXTENSIONS, MAX_VIDEO_SIZE, static_source_dir)
        video_url = _validate_https_url(project.get('video_url', ''), f'video_url de "{title}"')
        project_url = _validate_https_url(project.get('project_url', ''), f'project_url de "{title}"')
        if not any((image, video_file, video_url)):
            raise ValueError(f'El proyecto "{title}" necesita una imagen o un video.')

        published = project.get('published', True)
        if not isinstance(published, bool):
            raise ValueError(f'published de "{title}" debe ser true o false.')
        position = project.get('position', index)
        if not isinstance(position, int) or isinstance(position, bool) or position < 0:
            raise ValueError(f'position de "{title}" debe ser un entero no negativo.')
        if published:
            published_projects.append({
                'title': title,
                'description': description,
                'image': image,
                'video_file': video_file,
                'video_url': video_url,
                'project_url': project_url,
                'position': position,
                'created_order': index,
            })

    return sorted(published_projects, key=lambda project: (project['position'], project['created_order']))
