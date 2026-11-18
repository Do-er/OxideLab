import AppKit
import Foundation

func loadBitmap(svgURL: URL, size: Int) -> NSBitmapImageRep? {
    guard let image = NSImage(contentsOf: svgURL) else { return nil }
    guard let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size,
        pixelsHigh: size,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    ) else { return nil }

    rep.size = NSSize(width: size, height: size)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    NSColor.clear.set()
    NSRect(x: 0, y: 0, width: size, height: size).fill()
    image.draw(
        in: NSRect(x: 0, y: 0, width: size, height: size),
        from: .zero,
        operation: .sourceOver,
        fraction: 1.0
    )
    NSGraphicsContext.restoreGraphicsState()
    return rep
}

let args = CommandLine.arguments
if args.count == 3 && args[1] == "--bounds" {
    let svgURL = URL(fileURLWithPath: args[2])
    let size = 1024
    guard let rep = loadBitmap(svgURL: svgURL, size: size) else {
        fputs("Failed to render SVG: \(svgURL.path)\n", stderr)
        exit(1)
    }
    var minX = size, minY = size, maxX = -1, maxY = -1
    for y in 0..<size {
        for x in 0..<size {
            if let c = rep.colorAt(x: x, y: y), c.alphaComponent > 0.01 {
                if x < minX { minX = x }
                if x > maxX { maxX = x }
                if y < minY { minY = y }
                if y > maxY { maxY = y }
            }
        }
    }
    if maxX < minX || maxY < minY {
        fputs("SVG contains no visible pixels: \(svgURL.path)\n", stderr)
        exit(1)
    }
    let w = maxX - minX + 1
    let h = maxY - minY + 1
    let cx = Double(minX + maxX) / 2.0
    let cy = Double(minY + maxY) / 2.0
    print("\(cx) \(cy) \(w) \(h)")
    exit(0)
}

guard args.count == 4, let size = Int(args[3]), size > 0 else {
    fputs("Usage:\n  render_svg.swift <input.svg> <output.png> <size>\n  render_svg.swift --bounds <input.svg>\n", stderr)
    exit(1)
}

let inputURL = URL(fileURLWithPath: args[1])
let outputURL = URL(fileURLWithPath: args[2])
guard let rep = loadBitmap(svgURL: inputURL, size: size),
      let pngData = rep.representation(using: .png, properties: [:]) else {
    fputs("Failed to render PNG from \(inputURL.path)\n", stderr)
    exit(1)
}
try pngData.write(to: outputURL)
