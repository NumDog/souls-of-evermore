// qr.swift gen <text> <L|M|Q|H>  -> Matrix als Zeilen aus 0/1 (ohne Rand)
// qr.swift lies <png>            -> erkannte Texte
import Foundation
import CoreImage
import AppKit
let a = CommandLine.arguments
if a[1] == "gen" {
    let f = CIFilter(name: "CIQRCodeGenerator")!
    f.setValue(a[2].data(using: .isoLatin1), forKey: "inputMessage")
    f.setValue(a[3], forKey: "inputCorrectionLevel")
    let img = f.outputImage!
    let ext = img.extent
    let ctx = CIContext()
    let w = Int(ext.width), h = Int(ext.height)
    var buf = [UInt8](repeating: 0, count: w*h*4)
    ctx.render(img, toBitmap: &buf, rowBytes: w*4, bounds: ext, format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
    for y in 0..<h { var s = ""; for x in 0..<w { s += buf[(y*w+x)*4] < 128 ? "1" : "0" }; print(s) }
} else {
    let url = URL(fileURLWithPath: a[2])
    let ci = CIImage(contentsOf: url)!
    let det = CIDetector(ofType: CIDetectorTypeQRCode, context: nil, options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])!
    let fs = det.features(in: ci)
    if fs.isEmpty { print("NICHTS") }
    for f in fs { if let q = f as? CIQRCodeFeature { print(q.messageString ?? "?") } }
}
