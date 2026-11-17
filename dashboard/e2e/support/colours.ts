import type { Locator } from '@playwright/test';

/** A colour as painted on the screen, each channel from 0 to 255; alpha 0 is a transparent colour. */
export type Rgb = {
  readonly red: number;
  readonly green: number;
  readonly blue: number;
  readonly alpha: number;
};

type ColourProperty = 'color' | 'backgroundColor' | 'borderBottomColor';

// The browser writes colours in the space the style chose (oklch for Tailwind): painted on a canvas they read as RGB.
export const paintedColourOf = async (locator: Locator, property: ColourProperty): Promise<Rgb> => {
  const [red = 0, green = 0, blue = 0, alpha = 0] = await locator.evaluate((element, name) => {
    const context = document.createElement('canvas').getContext('2d');
    if (context === null) {
      return [];
    }
    context.fillStyle = getComputedStyle(element)[name];
    context.fillRect(0, 0, 1, 1);
    return [...context.getImageData(0, 0, 1, 1).data];
  }, property);
  return { red, green, blue, alpha };
};

/** The colour the user sees: a transparent background shows the white of the page behind it. */
export const colourOf = async (locator: Locator, property: ColourProperty): Promise<Rgb> => {
  const colour = await paintedColourOf(locator, property);
  return colour.alpha === 0 ? { red: 255, green: 255, blue: 255, alpha: 255 } : colour;
};

export const isTransparent = ({ alpha }: Rgb): boolean => alpha === 0;

export const isWhite = ({ red, green, blue }: Rgb): boolean => Math.min(red, green, blue) > 240;

// A red tone: the red channel well above the other two, as the commands that destroy.
export const isRed = ({ red, green, blue }: Rgb): boolean =>
  red > 150 && red > 2 * Math.max(green, blue);

// A blue tone: the blue channel well above the other two, as the mark of the chosen tab.
export const isBlue = ({ red, green, blue, alpha }: Rgb): boolean =>
  alpha > 0 && blue > 100 && blue > 1.5 * Math.max(red, green);

// A green tone: the green channel well above the other two, as the commands that set a flow running.
export const isGreen = ({ red, green, blue }: Rgb): boolean =>
  green > 90 && green > 1.4 * Math.max(red, blue);

// An amber tone: much red, less green and almost no blue, as the command that holds a flow.
export const isAmber = ({ red, green, blue }: Rgb): boolean =>
  red > 180 && green > 70 && green < 0.8 * red && blue < 0.4 * green;

/** How light a colour looks, from 0 (black) to 255 (white). */
export const lightnessOf = ({ red, green, blue }: Rgb): number =>
  0.2126 * red + 0.7152 * green + 0.0722 * blue;
