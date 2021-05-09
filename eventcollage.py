# Very heavily based on github.com/sebbacon/photocollage-helper

from photocollage import collage, render
import math, os, random, sys

class UserCollage(object):
    """Represents a user-defined collage
    A UserCollage contains a list of photos (referenced by filenames) and a
    collage.Page object describing their layout in a final poster.
    """

    def __init__(self, photolist):
        self.photolist = photolist

    def make_page(self, opts):
        ratio = 1.0 * opts.out_h / opts.out_w

        avg_ratio = sum(1.0 * photo.h / photo.w for photo in self.photolist) / len(
            self.photolist
        )
        virtual_no_imgs = 2 * len(self.photolist)
        no_cols = int(round(math.sqrt(avg_ratio / ratio * virtual_no_imgs)))

        self.page = collage.Page(1.0, ratio, no_cols)
        random.shuffle(self.photolist)
        for photo in self.photolist:
            self.page.add_cell(photo)
        self.page.adjust()

    def duplicate(self):
        return UserCollage(copy.copy(self.photolist))


class Options(object):
    def __init__(self, width, height, border_width, border_colour):
        self.border_w = border_width / 100
        self.border_c = border_colour
        self.out_w = width
        self.out_h = height


def save_poster(savefile, opts, collage):
    enlargement = float(opts.out_w) / collage.page.w
    collage.page.scale(enlargement)
    t = render.RenderingTask(
        collage.page,
        output_file=savefile,
        border_width=opts.border_w * max(collage.page.w, collage.page.h),
        border_color=opts.border_c,
    )
    t.start()
    return t


def make_collage(filename, new_images, width, height):
    photolist = []
    photolist.extend(render.build_photolist(new_images))
    opts = Options(width, height, 1, 'black')
    if len(photolist) > 0:
        new_collage = UserCollage(photolist)
        new_collage.make_page(opts)
        save_poster(filename, opts, new_collage).join()
        return filename
    return ''
