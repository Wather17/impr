import os
import sys
import re
import zipfile
import tempfile
import shutil
import subprocess
import posixpath
import urllib.parse
import xml.etree.ElementTree as ET
import argparse
from pypdf import PdfReader, PdfWriter, PageObject, Transformation

def find_browser():
    """Busca automaticamente caminhos comuns do Brave e Edge no Windows."""
    paths = [
        # Brave Browser
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        # Microsoft Edge
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def find_opf_path(temp_dir):
    """Encontra o arquivo .opf a partir do container.xml."""
    container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
    if not os.path.exists(container_path):
        raise FileNotFoundError("Não foi possível encontrar META-INF/container.xml no EPUB.")
    
    tree = ET.parse(container_path)
    root = tree.getroot()
    
    rootfile = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
    if rootfile is None:
        rootfile = root.find('.//rootfile')
        
    if rootfile is not None:
        return rootfile.get('full-path')
    
    raise FileNotFoundError("Caminho do arquivo OPF não especificado no container.xml.")

def parse_opf(temp_dir, opf_rel_path):
    """Lê o OPF, extrai os itens do manifesto e a ordem de leitura do spine."""
    opf_full_path = os.path.join(temp_dir, opf_rel_path)
    if not os.path.exists(opf_full_path):
        raise FileNotFoundError(f"Arquivo OPF não encontrado em: {opf_full_path}")
        
    tree = ET.parse(opf_full_path)
    root = tree.getroot()
    
    ns = {'opf': 'http://www.idpf.org/2007/opf'}
    
    # Manifesto: mapeia ID para href
    manifest = {}
    manifest_elem = root.find('.//opf:manifest', ns)
    if manifest_elem is None:
        manifest_elem = root.find('.//manifest')
        
    if manifest_elem is not None:
        items = manifest_elem.findall('.//opf:item', ns) or manifest_elem.findall('.//item')
        for item in items:
            manifest[item.get('id')] = item.get('href')
            
    # Spine: ordem dos capítulos
    spine_elem = root.find('.//opf:spine', ns)
    if spine_elem is None:
        spine_elem = root.find('.//spine')
        
    spine_items = []
    if spine_elem is not None:
        itemrefs = spine_elem.findall('.//opf:itemref', ns) or spine_elem.findall('.//itemref')
        for itemref in itemrefs:
            idref = itemref.get('idref')
            if idref in manifest:
                spine_items.append(manifest[idref])
                
    return spine_items

def parse_toc(temp_dir, opf_rel_path):
    """Parseia a tabela de conteúdos (TOC) para mapear caminhos de capítulos para títulos amigáveis."""
    opf_full_path = os.path.join(temp_dir, opf_rel_path)
    opf_dir = os.path.dirname(opf_rel_path)
    
    try:
        tree = ET.parse(opf_full_path)
        root = tree.getroot()
        ns = {'opf': 'http://www.idpf.org/2007/opf'}
        
        # Descobrir o id do ncx na tag <spine toc="...">
        spine_elem = root.find('.//opf:spine', ns)
        if spine_elem is None:
            spine_elem = root.find('.//spine')
            
        toc_id = spine_elem.get('toc') if spine_elem is not None else None
        
        # Descobrir o href do toc no manifesto
        toc_href = None
        manifest_elem = root.find('.//opf:manifest', ns)
        if manifest_elem is None:
            manifest_elem = root.find('.//manifest')
            
        if manifest_elem is not None:
            if toc_id:
                for item in manifest_elem.findall('.//opf:item', ns) or manifest_elem.findall('.//item'):
                    if item.get('id') == toc_id:
                        toc_href = item.get('href')
                        break
            if not toc_href:
                for item in manifest_elem.findall('.//opf:item', ns) or manifest_elem.findall('.//item'):
                    if item.get('media-type') == 'application/x-dtbncx+xml':
                        toc_href = item.get('href')
                        break
                        
        if not toc_href:
            return {}
            
        toc_full_path = os.path.join(temp_dir, opf_dir, toc_href)
        if not os.path.exists(toc_full_path):
            return {}
            
        # Parsear o arquivo toc.ncx
        toc_tree = ET.parse(toc_full_path)
        toc_root = toc_tree.getroot()
        ncx_ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
        
        toc_map = {}
        nav_points = toc_root.findall('.//ncx:navPoint', ncx_ns)
        if not nav_points:
            nav_points = toc_root.findall('.//navPoint')
            
        toc_dir = os.path.dirname(toc_href)
        
        for np in nav_points:
            text_elem = np.find('.//ncx:text', ncx_ns)
            if text_elem is None:
                text_elem = np.find('.//text')
                
            content_elem = np.find('.//ncx:content', ncx_ns)
            if content_elem is None:
                content_elem = np.find('.//content')
            
            if text_elem is not None and content_elem is not None:
                title = text_elem.text
                src = content_elem.get('src')
                if title and src:
                    title = title.strip()
                    src_clean = src.split('#')[0]
                    src_rel_to_opf = posixpath.normpath(posixpath.join(toc_dir, src_clean))
                    
                    if src_rel_to_opf in toc_map:
                        old_title = toc_map[src_rel_to_opf]
                        cleaned_old = old_title.strip().replace('.', '')
                        if len(old_title) <= 4 and (cleaned_old.isdigit() or cleaned_old.lower() in ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']) and old_title != title:
                            toc_map[src_rel_to_opf] = f"{old_title} - {title}"
                    else:
                        toc_map[src_rel_to_opf] = title
                        
        return toc_map
    except Exception as e:
        print(f"Aviso ao ler tabela de conteúdos: {e}")
        return {}

def get_chapter_title(temp_dir, opf_dir, href, index, toc_map):
    """Obtém o título amigável do capítulo usando a TOC ou a tag <title> do HTML."""
    normalized_href = posixpath.normpath(href)
    if normalized_href in toc_map:
        return toc_map[normalized_href]
        
    cap_file_path = os.path.join(temp_dir, opf_dir, href)
    if os.path.exists(cap_file_path):
        try:
            with open(cap_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.DOTALL | re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'\s+', ' ', title)
                if title and title.lower() not in ['untitled', 'sem tıtulo', 'capítulo', 'cover']:
                    return title
        except Exception:
            pass
            
    basename = os.path.basename(href)
    name_without_ext = os.path.splitext(basename)[0]
    if len(name_without_ext) > 20 or re.match(r'^[a-f0-9_\-]+$', name_without_ext, re.I):
        return f"Capítulo {index + 1}"
    return name_without_ext

def parse_chapters_selection(selection_str, total_chapters):
    """Converte strings como '1-3,5' em uma lista de índices 0-indexed."""
    if not selection_str.strip():
        return list(range(total_chapters))
        
    selected_indices = set()
    parts = selection_str.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start_str, end_str = part.split('-')
                start = int(start_str.strip()) - 1
                end = int(end_str.strip()) - 1
                start = max(0, min(start, total_chapters - 1))
                end = max(0, min(end, total_chapters - 1))
                for i in range(min(start, end), max(start, end) + 1):
                    selected_indices.add(i)
            except ValueError:
                print(f"Aviso: Intervalo inválido '{part}' ignorado.")
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < total_chapters:
                    selected_indices.add(idx)
                else:
                    print(f"Aviso: Índice de capítulo {part} fora do limite (1-{total_chapters}) ignorado.")
            except ValueError:
                print(f"Aviso: Capítulo inválido '{part}' ignorado.")
                
    if not selected_indices:
        print("Nenhum capítulo válido selecionado. Processando todo o livro.")
        return list(range(total_chapters))
        
    return sorted(list(selected_indices))

def adjust_image_sources(html_content, cap_zip_path):
    """Corrige caminhos de imagens locais para serem relativos à raiz de extração do ZIP."""
    cap_dir = posixpath.dirname(cap_zip_path)
    
    def repl_img(match):
        attrs = match.group(1)
        src_match = re.search(r'src=["\'](.*?)["\']', attrs)
        if src_match:
            src = src_match.group(1)
            if not (src.startswith('http://') or src.startswith('https://') or src.startswith('data:')):
                src_decoded = urllib.parse.unquote(src)
                zip_path = posixpath.normpath(posixpath.join(cap_dir, src_decoded))
                new_src = urllib.parse.quote(zip_path)
                attrs = attrs.replace(src, new_src)
        return f'<img {attrs}>'
        
    def repl_svg_image(match):
        attrs = match.group(1)
        href_match = re.search(r'(?:xlink:)?href=["\'](.*?)["\']', attrs)
        if href_match:
            href = href_match.group(1)
            if not (href.startswith('http://') or href.startswith('https://') or href.startswith('data:')):
                href_decoded = urllib.parse.unquote(href)
                zip_path = posixpath.normpath(posixpath.join(cap_dir, href_decoded))
                new_href = urllib.parse.quote(zip_path)
                attrs = attrs.replace(href, new_href)
        return f'<image {attrs}>'

    html_content = re.sub(r'<img\s+([^>]*?)>', repl_img, html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'<image\s+([^>]*?)>', repl_svg_image, html_content, flags=re.IGNORECASE)
    return html_content

def consolidate_chapters(temp_dir, opf_rel_path, chapter_hrefs, output_html_path, font_size, margin, font_family):
    """Extrai o body de todos os capítulos selecionados, corrige referências e gera um HTML único."""
    opf_dir = os.path.dirname(opf_rel_path)
    
    injected_css = f"""
    @media print {{
      @page {{
        size: 148mm 210mm; /* A5 Retrato */
        margin: {margin} !important;
      }}
    }}
    body {{
      font-family: "{font_family}", serif !important;
      font-size: {font_size} !important;
      line-height: 1.5 !important;
      color: #000000 !important;
      background: transparent !important;
      text-align: justify !important;
      margin: 0 !important;
      padding: 0 !important;
    }}
    p, span, div, li, td {{
      font-family: "{font_family}", serif !important;
      font-size: {font_size} !important;
      line-height: 1.5 !important;
      text-align: justify !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: "{font_family}", serif !important;
      color: #000000 !important;
      page-break-after: avoid !important;
      break-after: avoid !important;
    }}
    .chapter-break {{
      page-break-before: always !important;
      break-before: always !important;
      height: 0;
      margin: 0;
      padding: 0;
      border: none;
    }}
    img {{
      max-width: 100% !important;
      max-height: 90vh !important;
      display: block !important;
      margin: 15px auto !important;
      object-fit: contain !important;
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }}
    table, pre, blockquote {{
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }}
    """
    
    bodies = []
    for idx, href in enumerate(chapter_hrefs):
        cap_zip_path = posixpath.normpath(posixpath.join(opf_dir, href))
        cap_file_path = os.path.join(temp_dir, cap_zip_path)
        
        if not os.path.exists(cap_file_path):
            print(f"Aviso: Capítulo '{href}' não encontrado no caminho: {cap_file_path}. Ignorado.")
            continue
            
        with open(cap_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
        body_content = body_match.group(1) if body_match else content
        
        body_content = adjust_image_sources(body_content, cap_zip_path)
        
        break_html = "" if idx == 0 else '<div class="chapter-break"></div>'
        bodies.append(f"{break_html}\n<div class='chapter-container'>\n{body_content}\n</div>")
        
    consolidated_content = "\n".join(bodies)
    
    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Livro Otimizado para Impressão</title>
  <style>
    {injected_css}
  </style>
</head>
<body>
  {consolidated_content}
</body>
</html>
"""
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

def convert_html_to_pdf(html_path, pdf_path, browser_path):
    """Invoca o navegador em modo Headless para gerar o PDF intermediário A5."""
    args = [
        browser_path,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path}",
        "--no-margins",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        html_path
    ]
    print(f"Renderizando HTML para PDF A5 usando {os.path.basename(browser_path)}...")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print("Erro durante a conversão del navegador:")
        print(result.stderr)
        raise RuntimeError(f"O navegador falhou com código {result.returncode}")
    print("PDF A5 intermediário gerado.")

def generate_page_numbers_pdf(num_pages, output_pdf_path, browser_path, temp_dir):
    """Gera um PDF A5 contendo apenas os números das páginas centralizados no rodapé."""
    html_path = os.path.join(temp_dir, "numbers.html")
    
    pages_html = []
    for i in range(1, num_pages + 1):
        pages_html.append(f'<div class="page-container"><div class="num">{i}</div></div>')
        
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @media print {{
      @page {{
        size: 148mm 210mm; /* A5 */
        margin: 0 !important;
      }}
      body {{
        margin: 0 !important;
        padding: 0 !important;
      }}
    }}
    body {{
      margin: 0;
      padding: 0;
      font-family: Arial, sans-serif;
    }}
    .page-container {{
      width: 148mm;
      height: 210mm;
      position: relative;
      page-break-after: always;
      box-sizing: border-box;
    }}
    .page-container:last-child {{
      page-break-after: avoid;
    }}
    .num {{
      position: absolute;
      bottom: 8mm; /* Posição do rodapé */
      left: 0;
      right: 0;
      text-align: center;
      font-size: 9pt;
      color: #666666;
    }}
  </style>
</head>
<body>
  {"".join(pages_html)}
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    convert_html_to_pdf(html_path, output_pdf_path, browser_path)

def merge_page_to_half(target_page, source_page, is_right, a4_width=841.89, a4_height=595.275):
    """Posiciona e escala uma página A5 em uma das metades da folha A4 Paisagem."""
    src_width = float(source_page.mediabox.width)
    src_height = float(source_page.mediabox.height)
    
    dest_width = a4_width / 2.0
    dest_height = a4_height
    
    scale = min(dest_width / src_width, dest_height / src_height)
    
    scaled_w = src_width * scale
    scaled_h = src_height * scale
    
    dx = (dest_width - scaled_w) / 2.0
    dy = (dest_height - scaled_h) / 2.0
    
    if is_right:
        dx += dest_width
        
    op = Transformation().scale(scale).translate(dx, dy)
    target_page.merge_transformed_page(source_page, op)

def impose_pdf(input_pdf_path, output_pdf_path, mode, signature_size=16, line_page=None):
    """Lê o PDF A5 e gera o PDF final A4 Paisagem aplicando a imposição e linha de corte central."""
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    
    num_pages = len(reader.pages)
    
    a4_width = 841.89
    a4_height = 595.275
    
    logical_pages = []
    
    if mode in ['cut-stack', 'sequencial']:
        total_pages_needed = ((num_pages + 3) // 4) * 4
    elif mode == 'booklet':
        total_pages_needed = ((num_pages + signature_size - 1) // signature_size) * signature_size
    else:
        total_pages_needed = ((num_pages + 3) // 4) * 4
        
    for idx in range(total_pages_needed):
        if idx < num_pages:
            logical_pages.append(reader.pages[idx])
        else:
            first = reader.pages[0]
            logical_pages.append(PageObject.create_blank_page(width=first.mediabox.width, height=first.mediabox.height))
            
    total_physical_pages = total_pages_needed // 4
    print(f"Imprimindo em {total_physical_pages} folhas A4 físicas (Frente e Verso)...")
    
    if mode == 'sequencial':
        for i in range(total_physical_pages):
            frente = PageObject.create_blank_page(width=a4_width, height=a4_height)
            merge_page_to_half(frente, logical_pages[4*i], is_right=False)
            merge_page_to_half(frente, logical_pages[4*i+1], is_right=True)
            if line_page:
                frente.merge_page(line_page)
            writer.add_page(frente)
            
            verso = PageObject.create_blank_page(width=a4_width, height=a4_height)
            merge_page_to_half(verso, logical_pages[4*i+2], is_right=False)
            merge_page_to_half(verso, logical_pages[4*i+3], is_right=True)
            if line_page:
                verso.merge_page(line_page)
            writer.add_page(verso)
            
    elif mode == 'cut-stack':
        F = total_physical_pages
        for i in range(F):
            frente = PageObject.create_blank_page(width=a4_width, height=a4_height)
            merge_page_to_half(frente, logical_pages[2*i], is_right=False)
            merge_page_to_half(frente, logical_pages[2*F + 2*i], is_right=True)
            if line_page:
                frente.merge_page(line_page)
            writer.add_page(frente)
            
            verso = PageObject.create_blank_page(width=a4_width, height=a4_height)
            merge_page_to_half(verso, logical_pages[2*F + 2*i + 1], is_right=False)
            merge_page_to_half(verso, logical_pages[2*i + 1], is_right=True)
            if line_page:
                verso.merge_page(line_page)
            writer.add_page(verso)
            
    elif mode == 'booklet':
        C = signature_size
        num_signatures = total_pages_needed // C
        
        for sig_idx in range(num_signatures):
            start = sig_idx * C
            end = start + C - 1
            F_cad = C // 4
            
            for i in range(F_cad):
                frente = PageObject.create_blank_page(width=a4_width, height=a4_height)
                merge_page_to_half(frente, logical_pages[end - 2*i], is_right=False)
                merge_page_to_half(frente, logical_pages[start + 2*i], is_right=True)
                if line_page:
                    frente.merge_page(line_page)
                writer.add_page(frente)
                
                verso = PageObject.create_blank_page(width=a4_width, height=a4_height)
                merge_page_to_half(verso, logical_pages[start + 2*i + 1], is_right=False)
                merge_page_to_half(verso, logical_pages[end - 2*i - 1], is_right=True)
                if line_page:
                    verso.merge_page(line_page)
                writer.add_page(verso)
                
    with open(output_pdf_path, 'wb') as out_f:
        writer.write(out_f)
    print(f"PDF final com imposição gravado com sucesso em: {output_pdf_path}")

def run_pipeline(epub_path, output_pdf_path, font_size, margin, font_family, mode, signature_size, chapters_filter=None, browser_path=None):
    """Coordena todas as etapas do processo."""
    if not browser_path:
        browser_path = find_browser()
        if not browser_path:
            raise RuntimeError("Não foi possível encontrar nenhum navegador compatível (Brave ou Edge).")
            
    print(f"Navegador selecionado: {browser_path}")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Gerar o PDF temporário contendo apenas a linha de corte vertical central
        html_line_path = os.path.join(temp_dir, "line.html")
        pdf_line_path = os.path.join(temp_dir, "line.pdf")
        
        line_html_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @media print {
      @page {
        size: 297mm 210mm; /* A4 Paisagem */
        margin: 0 !important;
      }
      body {
        margin: 0 !important;
        padding: 0 !important;
      }
    }
    body {
      width: 297mm;
      height: 210mm;
      margin: 0;
      padding: 0;
      overflow: hidden;
    }
    .cut-line {
      position: absolute;
      left: 148.5mm; /* Meio exato de 297mm */
      top: 5mm;
      bottom: 5mm;
      width: 0;
      height: 200mm;
      border-left: 1px dashed #cccccc; /* Linha pontilhada cinza claro */
    }
  </style>
</head>
<body>
  <div class="cut-line"></div>
</body>
</html>
"""
        with open(html_line_path, 'w', encoding='utf-8') as f:
            f.write(line_html_content)
            
        convert_html_to_pdf(html_line_path, pdf_line_path, browser_path)
        
        line_reader = PdfReader(pdf_line_path)
        line_page = line_reader.pages[0]
        
        # 2. Extrair EPUB
        print(f"Extraindo EPUB '{epub_path}'...")
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        opf_rel_path = find_opf_path(temp_dir)
        print(f"Arquivo OPF encontrado: {opf_rel_path}")
        
        chapter_hrefs = parse_opf(temp_dir, opf_rel_path)
        total_chapters = len(chapter_hrefs)
        print(f"Total de capítulos no livro: {total_chapters}")
        
        opf_dir = os.path.dirname(opf_rel_path)
        toc_map = parse_toc(temp_dir, opf_rel_path)
        
        # Definir caminho do PDF de saída dinamicamente se não especificado
        if not output_pdf_path:
            base_epub_name = os.path.basename(epub_path)
            name_without_ext = os.path.splitext(base_epub_name)[0]
            
            # Divide o nome por espaços, sublinhados ou hifens e pega as 3 primeiras partes
            parts = [p.strip() for p in re.split(r'[\s_\-]+', name_without_ext) if p.strip()]
            book_short_name = "_".join(parts[:3])
            if len(book_short_name) > 30:
                book_short_name = book_short_name[:30].rstrip('_')
                
            if chapters_filter:
                selected_indices = parse_chapters_selection(chapters_filter, total_chapters)
                if len(selected_indices) == 1:
                    idx = selected_indices[0]
                    cap_title = get_chapter_title(temp_dir, opf_dir, chapter_hrefs[idx], idx, toc_map)
                    # Sanitiza o título do capítulo
                    cap_title_clean = re.sub(r'[\\/*?:"<>|]', "", cap_title)
                    cap_title_clean = re.sub(r'[\s_\-]+', "_", cap_title_clean).strip('_')
                    if len(cap_title_clean) > 15:
                        cap_title_clean = cap_title_clean[:15].rstrip('_')
                    ch_suffix = f"_Cap{idx+1:02d}_{cap_title_clean}"
                else:
                    is_sequential = all(selected_indices[i] + 1 == selected_indices[i+1] for i in range(len(selected_indices)-1))
                    if is_sequential:
                        ch_suffix = f"_Cap{selected_indices[0]+1:02d}-{selected_indices[-1]+1:02d}"
                    else:
                        ch_list_str = "_".join(f"{i+1:02d}" for i in selected_indices[:3])
                        if len(selected_indices) > 3:
                            ch_list_str += "_etc"
                        ch_suffix = f"_Cap{ch_list_str}"
            else:
                ch_suffix = "_Completo"
                
            pdf_dir = "pdf"
            os.makedirs(pdf_dir, exist_ok=True)
            output_pdf_path = os.path.join(pdf_dir, f"{book_short_name}{ch_suffix}.pdf")
            print(f"Caminho do PDF de saída definido automaticamente: {output_pdf_path}")
            
        if chapters_filter:
            selected_indices = parse_chapters_selection(chapters_filter, total_chapters)
            print(f"Filtro aplicado: capítulos {', '.join(str(i+1) for i in selected_indices)}")
            
            for idx in selected_indices:
                title = get_chapter_title(temp_dir, opf_dir, chapter_hrefs[idx], idx, toc_map)
                print(f"  -> Incluindo: {title}")
                
            chapter_hrefs = [chapter_hrefs[i] for i in selected_indices]
        
        # 3. HTML temporário consolidado
        html_consolidated = os.path.join(temp_dir, "consolidated.html")
        consolidate_chapters(
            temp_dir=temp_dir,
            opf_rel_path=opf_rel_path,
            chapter_hrefs=chapter_hrefs,
            output_html_path=html_consolidated,
            font_size=font_size,
            margin=margin,
            font_family=font_family
        )
        
        # 4. Gerar o PDF A5 bruto (sem paginação no rodapé)
        temp_pdf_a5_raw = os.path.join(temp_dir, "temp_a5_raw.pdf")
        convert_html_to_pdf(html_consolidated, temp_pdf_a5_raw, browser_path)
        
        # 5. Ler as páginas A5 para gerar o PDF de numeração
        reader_a5 = PdfReader(temp_pdf_a5_raw)
        num_pages_logical = len(reader_a5.pages)
        print(f"Total de páginas lógicas geradas no A5: {num_pages_logical}")
        
        # 6. Gerar PDF contendo apenas os números das páginas nas mesmas dimensões A5
        temp_pdf_numbers = os.path.join(temp_dir, "temp_numbers.pdf")
        generate_page_numbers_pdf(num_pages_logical, temp_pdf_numbers, browser_path, temp_dir)
        
        # 7. Mesclar os números no PDF A5 bruto
        reader_numbers = PdfReader(temp_pdf_numbers)
        writer_numbered = PdfWriter()
        
        pages_to_process = min(len(reader_a5.pages), len(reader_numbers.pages))
        for i in range(pages_to_process):
            page_a5 = reader_a5.pages[i]
            page_num = reader_numbers.pages[i]
            page_a5.merge_page(page_num)
            writer_numbered.add_page(page_a5)
            
        temp_pdf_a5_numbered = os.path.join(temp_dir, "temp_a5_numbered.pdf")
        with open(temp_pdf_a5_numbered, 'wb') as f_out:
            writer_numbered.write(f_out)
        
        # 8. Imposição final com a linha de corte
        impose_pdf(temp_pdf_a5_numbered, output_pdf_path, mode, signature_size, line_page)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Limpeza de arquivos temporários concluída.")

def main():
    parser = argparse.ArgumentParser(description="Conversor de EPUB para PDF otimizado para impressão econômica (4 páginas por folha A4 frente/verso).")
    parser.add_argument("epub", nargs="?", help="Caminho do arquivo EPUB de entrada.")
    parser.add_argument("-o", "--output", help="Caminho do PDF de saída.")
    parser.add_argument("-f", "--font-size", default="12.5pt", help="Tamanho da fonte (padrão: 12.5pt).")
    parser.add_argument("-m", "--margin", default="15mm", help="Margem do PDF A5 (padrão: 15mm).")
    parser.add_argument("--font-family", default="serif", help="Família da fonte (padrão: serif).")
    parser.add_argument("--mode", default="cut-stack", choices=["cut-stack", "sequencial", "booklet"], help="Modo de imposição (padrão: cut-stack).")
    parser.add_argument("-s", "--signature-size", type=int, default=16, help="Tamanho do caderno para livreto, deve ser múltiplo de 4 (padrão: 16).")
    parser.add_argument("-c", "--chapters", help="Intervalo de capítulos a processar (ex: '1-3', '2,4', '5'). Padrão: todos.")
    parser.add_argument("--browser", help="Caminho para o executável do Brave ou Edge.")
    
    args = parser.parse_args()
    
    # Garantir que as pastas epub e pdf existam
    epub_dir = "epub"
    pdf_dir = "pdf"
    os.makedirs(epub_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    
    if not args.epub:
        print("=== CONVERSOR DE EPUB PARA PDF DE IMPRESSÃO ECONÔMICA ===")
        
        epubs = [f for f in os.listdir(epub_dir) if f.lower().endswith('.epub') and os.path.isfile(os.path.join(epub_dir, f))]
        
        epub = ""
        if epubs:
            print(f"\nEncontramos {len(epubs)} arquivo(s) EPUB na pasta '{epub_dir}':")
            for idx, f in enumerate(epubs):
                print(f"  {idx + 1}: {f}")
            print("  0: Digitar caminho manualmente...")
            
            selection = input(f"Selecione o arquivo (0-{len(epubs)}) [padrão: 1]: ").strip()
            if not selection:
                epub = os.path.join(epub_dir, epubs[0])
            elif selection == '0':
                epub = input("Digite o caminho do arquivo EPUB: ").strip().strip('"')
            else:
                try:
                    sel_idx = int(selection) - 1
                    if 0 <= sel_idx < len(epubs):
                        epub = os.path.join(epub_dir, epubs[sel_idx])
                    else:
                        print("Opção inválida. Digite o caminho manualmente.")
                        epub = input("Digite o caminho do arquivo EPUB: ").strip().strip('"')
                except ValueError:
                    cleaned_sel = selection.strip('"')
                    if os.path.exists(cleaned_sel):
                        epub = cleaned_sel
                    elif os.path.exists(os.path.join(epub_dir, cleaned_sel)):
                        epub = os.path.join(epub_dir, cleaned_sel)
                    else:
                        print("Entrada inválida. Digite o caminho manualmente.")
                        epub = input("Digite o caminho do arquivo EPUB: ").strip().strip('"')
        else:
            print(f"\nNenhum arquivo EPUB encontrado na pasta '{epub_dir}'.")
            epub = input("Digite o caminho do arquivo EPUB: ").strip().strip('"')
            
        if not epub or not os.path.exists(epub):
            print(f"Erro: Arquivo '{epub}' não encontrado.")
            sys.exit(1)
            
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(epub, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            opf_rel_path = find_opf_path(temp_dir)
            chapter_hrefs = parse_opf(temp_dir, opf_rel_path)
            opf_dir = os.path.dirname(opf_rel_path)
            
            toc_map = parse_toc(temp_dir, opf_rel_path)
            
            print(f"\nDetectamos {len(chapter_hrefs)} capítulos neste livro:")
            for idx, href in enumerate(chapter_hrefs):
                title = get_chapter_title(temp_dir, opf_dir, href, idx, toc_map)
                print(f"  {idx + 1}: {title}")
        except Exception as e:
            print(f"Erro ao ler os capítulos do livro: {e}")
            chapter_hrefs = []
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        print("\nSelecione o(s) capítulo(s) que você deseja imprimir:")
        print("-> Digite um intervalo como '2-4' (para capítulos 2, 3 e 4)")
        print("-> Digite capítulos separados por vírgula como '1,3,5'")
        print("-> Deixe em branco para processar o livro completo")
        ch_filter = input("Capítulos [padrão: todos]: ").strip()
        
        print("\nEscolha o formato de impressão (Template):")
        print("[1] Livreto Dobrado (Booklet) - Para dobrar as folhas ao meio e grampear/costurar.")
        print("    ➔ Imposição: booklet (cadernos de 16 páginas) | Margem: 15mm | Fonte: 12.5pt")
        print("[2] Cortado e Blocado (Cut & Stack) - Para cortar ao meio e colar/espiralar.")
        print("    ➔ Imposição: cut-stack | Margem: 15mm | Fonte: 12.5pt")
        print("[3] Personalizado (Avançado) - Permite escolher margem, fonte e imposição manualmente.")
        template_opt = input("Selecione a opção [padrão: 2]: ").strip()
        
        if not template_opt:
            template_opt = "2"
            
        sig_size = 16
        font_size = "12.5pt"
        margin = "15mm"
        mode = "cut-stack"
        
        if template_opt == "1":
            mode = "booklet"
            sig_size = 16
        elif template_opt == "3":
            print("\nEscolha o modo de imposição:")
            print("1: Corte e Empilhamento (Cut & Stack) - [Recomendado para cortar no meio com régua]")
            print("2: Sequencial Simples (2-up) - [Folha A4 inteira sem cortar, leitura esquerda -> direita]")
            print("3: Livreto (Booklet) - [Para dobrar a folha A4 ao meio sem cortar]")
            opt = input("Selecione o modo [padrão: 1]: ").strip()
            
            mode = "cut-stack"
            if opt == "2":
                mode = "sequencial"
            elif opt == "3":
                mode = "booklet"
                
            font_size = input("Digite o tamanho da fonte [padrão: 12.5pt]: ").strip() or "12.5pt"
            margin = input("Digite a margem da página [padrão: 15mm]: ").strip() or "15mm"
            
            if mode == "booklet":
                sig_in = input("Digite o tamanho do caderno (múltiplo de 4) [padrão: 16]: ").strip()
                if sig_in:
                    try:
                        sig_size = int(sig_in)
                        if sig_size % 4 != 0:
                            print("Erro: O tamanho do caderno deve ser múltiplo de 4. Usando padrão 16.")
                            sig_size = 16
                    except ValueError:
                        sig_size = 16
        else:
            mode = "cut-stack"
            
        output = input("Digite o caminho do PDF de saída (deixe em branco para automático): ").strip().strip('"')
        if not output:
            output = None
            
        run_pipeline(
            epub_path=epub,
            output_pdf_path=output,
            font_size=font_size,
            margin=margin,
            font_family="serif",
            mode=mode,
            signature_size=sig_size,
            chapters_filter=ch_filter,
            browser_path=None
        )
    else:
        if args.signature_size % 4 != 0:
            print("Erro: O tamanho do caderno (--signature-size) deve ser múltiplo de 4.")
            sys.exit(1)
            
        output_pdf = args.output
        if not output_pdf:
            output_pdf = None
            
        run_pipeline(
            epub_path=args.epub,
            output_pdf_path=output_pdf,
            font_size=args.font_size,
            margin=args.margin,
            font_family=args.font_family,
            mode=args.mode,
            signature_size=args.signature_size,
            chapters_filter=args.chapters,
            browser_path=args.browser
        )

if __name__ == "__main__":
    main()
