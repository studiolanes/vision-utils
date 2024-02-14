//
//  dimensionallyApp.swift
//  dimensionally
//
//  Created by Herrick Fang on 2/13/24.
//

import SwiftUI
import SwiftData
import AVFoundation
import UniformTypeIdentifiers

struct ImageRes {
    let width: Int
    let height: Int
    let bytesPerRow: Int
    let baseAddr: UnsafeMutableRawPointer
    let buffer: CVPixelBuffer
}

@main
struct dimensionallyApp: App {
  private func convertGrayscaleImageToPixelBuffer(imagePath: String) -> ImageRes? {
        guard let imageSource = CGImageSourceCreateWithURL(URL(fileURLWithPath: imagePath) as CFURL, nil),
              let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
            print("Unable to create image source.")
            return nil
        }
        
        let width = cgImage.width
        let height = cgImage.height
        
        var pixelBuffer: CVPixelBuffer?
   
        let status = CVPixelBufferCreate(kCFAllocatorDefault, width, height, kCVPixelFormatType_DepthFloat32, nil, &pixelBuffer)
        
        guard status == kCVReturnSuccess, let unwrappedPixelBuffer = pixelBuffer else {
            print("Error: Could not create pixel buffer, error code: \(status)")
            return nil
        }
        
        CVPixelBufferLockBaseAddress(unwrappedPixelBuffer, CVPixelBufferLockFlags(rawValue: 0))
        
      if let pixelData = CVPixelBufferGetBaseAddress(unwrappedPixelBuffer) {
          let bytesPerRow = CVPixelBufferGetBytesPerRow(unwrappedPixelBuffer)
          CVPixelBufferUnlockBaseAddress(unwrappedPixelBuffer, [])
          return ImageRes(width: width, height: height, bytesPerRow: bytesPerRow, baseAddr: pixelData, buffer: unwrappedPixelBuffer)
      } else {
          return nil
      }
    }
    
    private func hello() {
        guard let res = convertGrayscaleImageToPixelBuffer(imagePath: "/Users/herk/Downloads/depth_cat.jpg") else {
            print("Failed to create depth pixel buffer.")
            return
        }

        // Convert the pixel buffer to CFData
        let dataSize = CVPixelBufferGetDataSize(res.buffer)
        let depthDataCF = CFDataCreate(kCFAllocatorDefault, res.baseAddr.assumingMemoryBound(to: UInt8.self), dataSize)

        let depthDataInfo: [AnyHashable: Any] = [
            kCGImageAuxiliaryDataInfoData: depthDataCF!, // Your depth data as CFData
            kCGImageAuxiliaryDataInfoDataDescription: [
                kCGImagePropertyPixelFormat: kCVPixelFormatType_DepthFloat32, // Choose from the supported formats
                kCGImagePropertyWidth: res.width,
                kCGImagePropertyHeight: res.height,
                kCGImagePropertyBytesPerRow: res.bytesPerRow
            ],
            kCGImageAuxiliaryDataInfoMetadata: [:] // Optional metadata
        ]
        
        let depthData = try! AVDepthData(fromDictionaryRepresentation: depthDataInfo)
        
        // Ensure newImageURL is defined and points to a valid location on disk
        let newImageURL = URL(fileURLWithPath: "/Users/herk/Downloads/cat_with_depth.heic")
        
        guard let imageDataDestination = CGImageDestinationCreateWithURL(newImageURL as CFURL, UTType.heic.identifier as CFString, 1, nil) else {
            print("Failed to create image destination.")
            return
        }

        // Load the main image to which you want to attach the depth data
        let mainImageURL = URL(fileURLWithPath: "/Users/herk/Downloads/cat.heic")
        guard let mainImageSource = CGImageSourceCreateWithURL(mainImageURL as CFURL, nil),
              let mainImage = CGImageSourceCreateImageAtIndex(mainImageSource, 0, nil) else {
            print("Failed to load main image.")
            return
        }

        // Add the main image to the destination
        CGImageDestinationAddImage(imageDataDestination, mainImage, nil)

        var auxDataType: NSString?
        guard let auxData = depthData.dictionaryRepresentation(forAuxiliaryDataType: &auxDataType) else {
            print("Failed to get auxiliary data from depth data.")
            return
        }

        // Add the auxiliary depth data to the image destination
        CGImageDestinationAddAuxiliaryDataInfo(imageDataDestination, auxDataType!, auxData as CFDictionary)

        // Finalize the image destination to create the new image file with depth data
        if CGImageDestinationFinalize(imageDataDestination) {
            print("Depth data was successfully added to the image and saved.")
        } else {
            print("Failed to finalize the image destination.")
        }
    }
    
    func loadImage(at path: String) -> CGImage? {
        if let imageSource = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
            let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) {
            return cgImage
        } else {
            return nil
        }
    }
    
    func combineLeftandRight() {
        let leftImg = loadImage(at: "/Users/herk/Downloads/cart_left.png")!
        let rightImg = loadImage(at: "/Users/herk/Downloads/cart_right.png")!
        
        let newImageURL = URL(fileURLWithPath: "/Users/herk/Downloads/cart_with_depth.heic")
        let destination = CGImageDestinationCreateWithURL(newImageURL as CFURL, UTType.heic.identifier as CFString, 2, nil)!
        
        let imageWidth = CGFloat(leftImg.width)
        let imageHeight = CGFloat(leftImg.height)
        let fovHorizontalDegrees: CGFloat = 55
        let fovHorizontalRadians = fovHorizontalDegrees * (.pi / 180)
        let focalLengthPixels = 0.5 * imageWidth / tan(0.5 * fovHorizontalRadians)
        let baseline = 65.0 // in millimeters

        let cameraIntrinsics: [CGFloat] = [
            focalLengthPixels, 0, imageWidth / 2,
            0, focalLengthPixels, imageHeight / 2,
            0, 0, 1
        ]

        let properties = [
            kCGImagePropertyGroups: [
                kCGImagePropertyGroupIndex: 0,
                kCGImagePropertyGroupType: kCGImagePropertyGroupTypeStereoPair,
                kCGImagePropertyGroupImageIndexLeft: 0,
                kCGImagePropertyGroupImageIndexRight: 1,
            ],
            kCGImagePropertyHEIFDictionary: [
                kIIOMetadata_CameraModelKey: [
                    kIIOCameraModel_Intrinsics: cameraIntrinsics as CFArray
                ]
            ]
        ]

        CGImageDestinationAddImage(destination, leftImg, properties as CFDictionary)
        CGImageDestinationAddImage(destination, rightImg, properties as CFDictionary)
        CGImageDestinationFinalize(destination)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .task {
                    DispatchQueue.main.async {
                        self.combineLeftandRight()
                    }
                }
        }
    }
}
