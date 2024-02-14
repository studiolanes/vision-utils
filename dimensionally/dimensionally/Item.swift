//
//  Item.swift
//  dimensionally
//
//  Created by Herrick Fang on 2/13/24.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
