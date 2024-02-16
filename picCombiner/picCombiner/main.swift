//
//  main.swift
//  pngCombiner
//
//  Created by Herrick Fang on 2/14/24.
//

import Foundation
import AVFoundation
import UniformTypeIdentifiers
import ArgumentParser


struct PicCombiner: ParsableCommand {
    @Option(name: .shortAndLong, help: "The path to the left image.")
    var leftImagePath: String
    
    @Option(name: .shortAndLong, help: "The path to the right image.")
    var rightImagePath: String
    
    @Option(name: .shortAndLong, help: "The output path for the combined HEIC image.")
    var outputImagePath: String
    
    func run() throws {
        guard let leftImg = loadImage(at: leftImagePath) else {
            throw ValidationError("The left image could not be loaded.")
        }
        
        guard let rightImg = loadImage(at: rightImagePath) else {
            throw ValidationError("The right image could not be loaded.")
        }
        
        combineImages(leftImg: leftImg, rightImg: rightImg, outputPath: outputImagePath)
    }
    
    func loadImage(at path: String) -> CGImage? {
        if let imageSource = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
           let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) {
            return cgImage
        } else {
            return nil
        }
    }
    
    func combineImages(leftImg: CGImage, rightImg: CGImage, outputPath: String) {
        let newImageURL = URL(fileURLWithPath: outputPath)
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
}

PicCombiner.main()


