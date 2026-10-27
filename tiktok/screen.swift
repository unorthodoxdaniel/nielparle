// Reads the laptop screen in a clip: samples frames, runs Apple's text recognition on the
// bottom part of the frame (where the laptop sits) and prints one JSON line per frame:
// {"t": seconds, "lines": [...], "tops": [...]}, where tops[i] is the top of line i as a fraction of
// the full frame height (0 = top). Usage: screen <video> [step, default 0.5] [from] [to]
import AVFoundation
import Vision
import Foundation

let args = CommandLine.arguments
guard args.count >= 2 else { fputs("usage: screen <video> [step]\n", stderr); exit(1) }
let step = args.count > 2 ? Double(args[2])! : 0.5
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let duration = CMTimeGetSeconds(asset.duration)
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = CMTime(value: 1, timescale: 30)
gen.requestedTimeToleranceAfter = CMTime(value: 1, timescale: 30)
gen.maximumSize = CGSize(width: 1080, height: 1080)

var t = args.count > 3 ? Double(args[3])! : 0.0
let until = args.count > 4 ? min(Double(args[4])!, duration) : duration
while t < until {
  autoreleasepool {
    if let img = try? gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
      // laptop screen sits in the lower ~45% of the vertical frame
      let h = img.height, w = img.width
      let crop = img.cropping(to: CGRect(x: 0, y: Int(Double(h) * 0.5), width: w, height: h - Int(Double(h) * 0.5))) ?? img
      let req = VNRecognizeTextRequest()
      req.recognitionLanguages = ["fr-FR", "en-US"]
      req.recognitionLevel = .accurate
      req.usesLanguageCorrection = false
      try? VNImageRequestHandler(cgImage: crop).perform([req])
      let results = req.results ?? []
      let lines = results.map { $0.topCandidates(1)[0].string }
      // Vision boxes are normalised to the crop with the origin at the bottom left
      let tops = results.map { r -> Double in
        let topInCrop = 1.0 - Double(r.boundingBox.maxY)
        return ((0.5 + topInCrop * 0.5) * 1000).rounded() / 1000
      }
      let obj: [String: Any] = ["t": (t * 100).rounded() / 100, "lines": lines, "tops": tops]
      let data = try! JSONSerialization.data(withJSONObject: obj)
      print(String(data: data, encoding: .utf8)!)
      fflush(stdout)
    }
  }
  t += step
}
