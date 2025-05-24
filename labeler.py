import os
import re
import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab
import requests
from io import BytesIO
from tkinterdnd2 import DND_FILES, DND_TEXT, TkinterDnD
import urllib.parse
from bs4 import BeautifulSoup

LABELS_CSV = 'available_labels.csv'
ANNOTATIONS_CSV = 'annotations.csv'
SAVED_IMAGES_FOLDER = 'saved_images'
FOLDER_PATH_FILE = 'folder_path.txt'

def extract_image_source(data):
    """
    Given dropped data (as a string), try to extract a valid image source.
    Returns a tuple (source_type, source) where source_type is either 'file' or 'url'
    and source is the file path or URL. If extraction fails, returns (None, None).
    """
    data = data.strip('{}').strip()
    
    if os.path.isfile(data):
        return 'file', data

    if data.startswith('http://') or data.startswith('https://'):
        return 'url', data

    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', data, re.IGNORECASE)
    if img_match:
        return 'url', img_match.group(1)

    url_match = re.search(r'(https?://\S+)', data)
    if url_match:
        return 'url', url_match.group(1)

    return None, None

class LabelingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Labeling Tool")

        self.available_labels = self.load_available_labels()

        self.current_image = None  
        self.tk_image = None     
        self.current_image_path = None

        os.makedirs(SAVED_IMAGES_FOLDER, exist_ok=True)
        with open(FOLDER_PATH_FILE, 'w', encoding='utf-8') as f:
            f.write(os.path.abspath(SAVED_IMAGES_FOLDER))

        image_frame = tk.Frame(root)
        image_frame.pack(side=tk.TOP, padx=10, pady=10)

        self.canvas = tk.Canvas(image_frame, width=400, height=300, bg='gray')
        self.canvas.pack()
        self.canvas.drop_target_register(DND_FILES, DND_TEXT)
        self.canvas.dnd_bind('<<Drop>>', self.handle_drop)

        load_button = tk.Button(image_frame, text="Load Image", command=self.load_image)
        load_button.pack(pady=5)

        clipboard_button = tk.Button(image_frame, text="Get Image from Clipboard", command=self.load_image_from_clipboard)
        clipboard_button.pack(pady=5)

        labels_frame = tk.Frame(root)
        labels_frame.pack(side=tk.LEFT, padx=10, pady=10)

        tk.Label(labels_frame, text="Available Labels:").pack(anchor='w')
        self.labels_listbox = tk.Listbox(labels_frame, selectmode=tk.MULTIPLE, width=30, height=10)
        self.labels_listbox.pack()
        self.refresh_labels_listbox()

        tk.Label(labels_frame, text="Add new label:").pack(anchor='w', pady=(10, 0))
        self.new_label_entry = tk.Entry(labels_frame, width=25)
        self.new_label_entry.pack()
        add_label_button = tk.Button(labels_frame, text="Add Label", command=self.add_label)
        add_label_button.pack(pady=(5, 10))

        save_button = tk.Button(root, text="Save Image and Annotations", command=self.save_data)
        save_button.pack(pady=10)

    def load_available_labels(self):
        labels = []
        if os.path.exists(LABELS_CSV):
            with open(LABELS_CSV, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row:
                        labels.append(row[0])
        return labels

    def refresh_labels_listbox(self):
        self.labels_listbox.delete(0, tk.END)
        for label in self.available_labels:
            self.labels_listbox.insert(tk.END, label)

    def add_label(self):
        new_label = self.new_label_entry.get().strip()
        if new_label and new_label not in self.available_labels:
            self.available_labels.append(new_label)
            self.refresh_labels_listbox()
            self.save_available_labels()
            self.new_label_entry.delete(0, tk.END)
        elif new_label in self.available_labels:
            messagebox.showinfo("Info", "Label already exists.")
        else:
            messagebox.showwarning("Warning", "Please enter a valid label.")

    def save_available_labels(self):
        with open(LABELS_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for label in self.available_labels:
                writer.writerow([label])

    def load_image(self):
        filetypes = (("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(title="Open Image", filetypes=filetypes)
        if filename:
            self.load_image_from_path(filename)

    def load_image_from_path(self, filepath):
        try:
            self.current_image = Image.open(filepath)
            self.current_image_path = filepath
            self.display_image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image:\n{e}")

    def load_image_from_clipboard(self):
        try:
            im = ImageGrab.grabclipboard()
            if im:
                if isinstance(im, list) and len(im) > 0 and hasattr(im[0], 'copy'):
                    self.current_image = im[0]
                elif hasattr(im, 'copy'):
                    self.current_image = im
                else:
                    messagebox.showerror("Error", "No valid image found in clipboard.")
                    return
                self.current_image_path = "Clipboard"
                self.display_image()
            else:
                messagebox.showerror("Error", "No image found in clipboard.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image from clipboard:\n{e}")

    def load_image_from_url(self, url):
        if "wikipedia.org/wiki/File:" in url:
            direct_url = self.get_wikipedia_image_url(url)
            if direct_url:
                url = direct_url
            else:
                messagebox.showerror("Error", "Could not retrieve direct image URL from Wikipedia.")
                return

        if "google.com/url" in url:
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'url' in query_params:
                url = query_params['url'][0]
                
        if not url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            try:
                r = requests.get(url)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                meta = soup.find('meta', property='og:image')
                if meta and meta.get('content'):
                    extracted = meta.get('content')
                else:
                    img = soup.find('img')
                    if img and img.get('src'):
                        extracted = urllib.parse.urljoin(url, img.get('src'))
                    else:
                        extracted = url
                url = extracted
            except Exception as e:
                print("Error extracting image from HTML:", e)

        try:
            response = requests.get(url)
            response.raise_for_status()
            self.current_image = Image.open(BytesIO(response.content))
            self.current_image_path = url
            self.display_image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image from URL:\n{e}")

    def get_wikipedia_image_url(self, file_page_url):
        try:
            parsed_url = urllib.parse.urlparse(file_page_url)
            filename = parsed_url.path.split("/wiki/")[-1]
            api_url = ("https://en.wikipedia.org/w/api.php?action=query"
                       f"&titles={urllib.parse.quote(filename)}&prop=imageinfo&iiprop=url&format=json")
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo", [])
                if imageinfo:
                    return imageinfo[0].get("url")
        except Exception as e:
            print("Error retrieving Wikipedia image URL:", e)
            return None

    def display_image(self):
        max_size = (400, 300)
        image_copy = self.current_image.copy()
        image_copy.thumbnail(max_size)
        self.tk_image = ImageTk.PhotoImage(image_copy)
        self.canvas.delete("all")
        self.canvas.create_image(200, 150, image=self.tk_image)

    def handle_drop(self, event):
        source_type, source = extract_image_source(event.data)
        if source_type == 'file':
            self.load_image_from_path(source)
        elif source_type == 'url':
            self.load_image_from_url(source)
        else:
            messagebox.showwarning("Unsupported", "Could not extract an image from the dropped content.")

    def generate_ordinal_filename(self):
        existing = [f for f in os.listdir(SAVED_IMAGES_FOLDER) if f.startswith("image_")]
        next_index = 1
        if existing:
            nums = []
            for f in existing:
                try:
                    num = int(f.split('_')[1].split('.')[0])
                    nums.append(num)
                except Exception:
                    pass
            if nums:
                next_index = max(nums) + 1
        filename = f"image_{next_index:04d}.jpg"
        return os.path.join(SAVED_IMAGES_FOLDER, filename)

    def save_data(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "No image loaded!")
            return

        selected_indices = self.labels_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one label!")
            return
        selected_labels = [self.labels_listbox.get(i) for i in selected_indices]

        save_path = self.generate_ordinal_filename()
        try:
            self.current_image.save(save_path, "JPEG")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image:\n{e}")
            return

        labels_str = ";".join(selected_labels)
        file_exists = os.path.exists(ANNOTATIONS_CSV)
        try:
            with open(ANNOTATIONS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(["image_path", "labels"])
                writer.writerow([save_path, labels_str])
                self.current_image = None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write annotations:\n{e}")
            return

def main():
    root = TkinterDnD.Tk()
    app = LabelingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
