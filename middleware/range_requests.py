import os
import mimetypes
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class RangeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if "HTTP_RANGE" in request.META:
            return self.process_range_request(request)
        return None

    def process_range_request(self, request):
        # Prüfe, ob die Anfrage unter MEDIA_URL liegt
        if not request.path.startswith(settings.MEDIA_URL):
            return None

        # Relativen Pfad extrahieren
        relative_path = request.path[len(settings.MEDIA_URL):].lstrip('/')
        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        if not os.path.exists(file_path):
            return None

        file_size = os.path.getsize(file_path)
        range_header = request.META.get("HTTP_RANGE", "").strip()

        if not range_header.startswith('bytes='):
            return HttpResponse(status=400)

        byte_ranges = range_header[6:].split('-')
        if len(byte_ranges) != 2:
            return HttpResponse(status=400)

        start_str, end_str = byte_ranges

        # Suffix-Range (z.B. bytes=-500)
        if not start_str:
            if not end_str.isdigit():
                return HttpResponse(status=400)
            end = int(end_str)
            start = max(0, file_size - end)
            end = file_size - 1
        else:
            start = int(start_str)
            if not end_str:
                end = file_size - 1
            else:
                end = int(end_str)

        # Validiere den Bereich
        if start >= file_size or end >= file_size or start > end:
            response = HttpResponse(status=416)
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        end = min(end, file_size - 1)
        content_length = end - start + 1

        # Content-Type ermitteln
        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or 'application/octet-stream'

        # Streaming Response
        response = StreamingHttpResponse(
            self.file_iterator(file_path, start, end),
            status=206,
            content_type=content_type,
        )
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Content-Length'] = str(content_length)
        response['Accept-Ranges'] = 'bytes'
        return response

    def file_iterator(self, file_path, start, end, chunk_size=8192):
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
