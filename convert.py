from PIL import Image, ImageOps
import argparse
import sys
import os
from pathlib import Path

def brightness_step(pixel, output_steps, transparency):
    r = pixel[0] / 255.0
    g = pixel[1] / 255.0
    b = pixel[2] / 255.0
    a = pixel[3] / 255.0
    # luma calculation
    step = round((0.2126*r + 0.7152*g + 0.0722*b) * (output_steps-1))
    if a < 0.5 and transparency:
        step = -1
    return step

class IndexedImage:
    def __init__(self, image, name, output_steps, max_indexes, transparency=True):
        self.name          = name
        self.image         = image.convert("RGBA")
        self.width         = self.image.width
        self.height        = self.image.height
        self.indexed_image = []
        self.greyscale_with_transparency(output_steps, transparency)
        self.indexes = self.limit_indexes(output_steps, max_indexes, transparency)
        self.clamp_indexes()
        self.create_preview(output_steps, name)
        self.create_header()

    def create_header(self):
        output = ""
        output += f"// '{self.name}', {self.width}x{self.height}px\n"
        output += f"// indexes: {self.indexes}\n"
        output += f"const unsigned char {self.name.replace(' ', '_').replace('-', '_')}[] = " + "{\n"

        color = None
        run = 0
        line = "    0x{:02x}, 0x{:02x}, 0x{:02x}, 0x{:02x},".format(
                ((self.image.width & 0xFF00) >> 8) & 0x00FF,
                (self.image.width & 0xFF),
                ((self.image.height & 0xFF00) >> 8) & 0x00FF,
                (self.image.height & 0xFF)
        )
        byte_in_line = 5
        for y in range(len(self.indexed_image)):
            for x in range(len(self.indexed_image[y])):
                if color == None:
                    color = self.indexed_image[y][x]
                    continue
                if color != self.indexed_image[y][x] or run >= 0b00011111:
                    line += " 0x{:02x},".format((run << 3) | self.indexes.index(color))
                    run = -1
                    color = self.indexed_image[y][x]
                    if byte_in_line >= 16:
                        output += line + "\n"
                        line = "   "
                        byte_in_line = 0
                    byte_in_line += 1
                run += 1
        line += " 0x{:02x}".format((run << 3) | self.indexes.index(color))
        output += line + "\n};"
        with open(f"{self.name}.h", "w") as header:
            header.write(output)

    def create_preview(self, output_steps, name):
        preview = Image.new("LA", (self.width, self.height))
        for y in range(len(self.indexed_image)):
            for x in range(len(self.indexed_image[y])):
                luma  = round((self.indexed_image[y][x] / (output_steps-1)) * 255)
                alpha = round(0 if self.indexed_image[y][x] == -1 else 255)
                preview.putpixel((x, y), (luma if alpha == 255 else 0, alpha))
        preview.save(f"{name}_converted_preview.png")

    def clamp_indexes(self):
        for y in range(len(self.indexed_image)):
            for x in range(len(self.indexed_image[y])):
                if self.indexed_image[y][x] not in self.indexes:
                    self.indexed_image[y][x] = self.clamp_index(x,y)

    def clamp_index(self, x, y):
        index = self.indexed_image[y][x]
        stretch = 1
        while(True):
            if index + stretch in self.indexes:
                return index + stretch
            if index - stretch in self.indexes:
                return index - stretch
            stretch += 2

    def limit_indexes(self, output_steps, max_indexes, transparency):
        counters = {}
        counters[-1] = 0
        for i in range(output_steps):
            counters[i] = 0
        for y in range(len(self.indexed_image)):
            for x in range(len(self.indexed_image[y])):
                counters[self.indexed_image[y][x]] += 1
        while(len(counters) > max_indexes):
            smallest_amt   = None
            smallest_index = None
            for i in counters:
                if i == -1:
                    continue
                if i == 0 and counters[i] > 0:
                    continue
                if i == (output_steps-1) and counters[i] > 0:
                    continue
                if smallest_amt is None:
                    smallest_amt   = counters[i]
                    smallest_index = i
                    continue
                if counters[i] < smallest_amt:
                    smallest_amt   = counters[i]
                    smallest_index = i
            counters.pop(smallest_index)
        indexes = []
        for i in counters:
            indexes.append(i)
        return indexes

    def greyscale_with_transparency(self, output_steps, transparency):
        for y in range(self.height):
            self.indexed_image.append([])
            for x in range(self.width):
                step = brightness_step(self.image.getpixel((x,y)), output_steps, transparency)
                self.indexed_image[y].append(step)

def create_arg_parser():
    parser = argparse.ArgumentParser(description='Convert to PhobGCC images.')
    parser.add_argument('inputFile',
                    help='Path to the input file.')
    return parser

if __name__ == "__main__":
    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    if os.path.exists(parsed_args.inputFile):
        filestem = Path(parsed_args.inputFile).stem
        converted = IndexedImage(Image.open(parsed_args.inputFile), filestem, 10, 8)

    
